# rutele pt pagina de Statistics
# toate cer login si pot avea filtre: county / transaction_type / property_type

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import (
    Anunt,
    AppUser,
    Estate,
    IstoricAnunt,
    Judet,
    Localitate,
    TipImobil,
    TipTranzactie,
)
from backend.auth import get_current_user


router = APIRouter(prefix="/api/stats", tags=["stats"])


# doar 2 tranzactii valide
VALID_TRANSACTION_TYPES = {"vanzare", "inchiriere"}

# pun o limita sus la pret ca sa nu pice media (scraper vechi baga valori aiurea)
MAX_SANE_PRICE = 100_000_000


def _validate_filters(db: Session, county, transaction_type, property_type):
    # verific ca filtrele exista in DB, altfel dau 400
    if transaction_type and transaction_type not in VALID_TRANSACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail="transaction_type must be 'vanzare' or 'inchiriere'",
        )
    if county:
        exists = db.query(Judet).filter(Judet.nume_judet == county).first()
        if not exists:
            raise HTTPException(status_code=400, detail=f"Unknown county: {county}")
    if property_type:
        exists = (
            db.query(TipImobil).filter(TipImobil.nume_tip == property_type).first()
        )
        if not exists:
            raise HTTPException(
                status_code=400, detail=f"Unknown property_type: {property_type}"
            )


def _apply_filters(q, county, transaction_type, property_type):
    # pun WHERE-urile daca filtrele sunt setate
    # presupun ca query-ul are deja join-urile necesare
    if county:
        q = q.filter(Judet.nume_judet == county)
    if transaction_type:
        q = q.filter(TipTranzactie.nume_tranzactie == transaction_type)
    if property_type:
        q = q.filter(TipImobil.nume_tip == property_type)
    return q


# --- 1. trend pret pe luna ---
@router.get("/price-trend")
def price_trend(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # iau media pretului pe luna, dupa data din istoric
    month_col = func.to_char(IstoricAnunt.data_inceput, "YYYY-MM").label("month")

    q = (
        db.query(month_col, func.avg(IstoricAnunt.pret).label("avg_price"))
        .join(Anunt, Anunt.id_anunt == IstoricAnunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(IstoricAnunt.pret <= MAX_SANE_PRICE)
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(month_col).order_by(month_col).all()
    return [
        {"month": r.month, "average_price": round(float(r.avg_price))}
        for r in rows
        if r.avg_price is not None
    ]


# cate bucket-uri fac pe axa X
NUM_BUCKETS = 8


def _format_price_label(n):
    # 1500 -> 1.5k, 50000 -> 50k, 1200000 -> 1.2M
    if n >= 1_000_000:
        val = n / 1_000_000
        return f"{val:.1f}M" if val < 10 else f"{int(val)}M"
    if n >= 1000:
        val = n / 1000
        return f"{val:.1f}k" if val < 10 else f"{int(val)}k"
    return str(int(n))


# --- 2. distributia preturilor pe bucket-uri ---
@router.get("/price-distribution")
def price_distribution(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # intai iau min si max ca sa fac bucket-urile pe intervalul real
    base = (
        db.query(Anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(Anunt.pret.isnot(None))
        .filter(Anunt.pret > 0)
        .filter(Anunt.pret <= MAX_SANE_PRICE)
    )
    base = _apply_filters(base, county, transaction_type, property_type)

    mn, mx = base.with_entities(func.min(Anunt.pret), func.max(Anunt.pret)).one()

    if mn is None or mx is None:
        return []

    # daca toate sunt la fel fac un singur bucket
    if mn == mx:
        cnt = base.with_entities(func.count()).scalar() or 0
        return [{"range": _format_price_label(mn), "count": cnt}]

    # width_bucket imparte [mn, mx] in NUM_BUCKETS intervale egale
    # NUM_BUCKETS+1 e edge-ul cu valoarea maxima
    bucket_col = func.width_bucket(Anunt.pret, mn, mx, NUM_BUCKETS).label("b")

    q = base.with_entities(bucket_col, func.count().label("count")).group_by(bucket_col)
    rows = q.all()
    counts = {int(r.b): r.count for r in rows}

    # calculez marginile in Python
    step = (mx - mn) / NUM_BUCKETS
    result = []
    for i in range(1, NUM_BUCKETS + 1):
        lo = mn + step * (i - 1)
        hi = mn + step * i
        label = f"{_format_price_label(lo)}-{_format_price_label(hi)}"
        # valoarea maxima o pun tot in ultimul bucket
        count = counts.get(i, 0)
        if i == NUM_BUCKETS:
            count += counts.get(NUM_BUCKETS + 1, 0)
        result.append({"range": label, "count": count})

    return result


# --- 3. anunturi pe platforma ---
@router.get("/listings-per-platform")
def listings_per_platform(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # grupez dupa platforma din raw_data, deci pornesc de acolo
    q = (
        db.query(Estate.platforma.label("platform"), func.count().label("count"))
        .join(Anunt, Anunt.id_sursa_raw == Estate.id_raw)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(Estate.platforma).order_by(desc("count")).all()
    return [{"platform": r.platform or "necunoscut", "count": r.count} for r in rows]


# --- 4. pret mediu pe mp in fiecare oras ---
@router.get("/price-per-sqm")
def price_per_sqm(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # media din (pret / suprafata) pe oras
    # *1.0 ca sa nu faca impartire intreaga
    pps = func.avg(Anunt.pret * 1.0 / Anunt.suprafata).label("pps")
    cnt = func.count().label("cnt")

    q = (
        db.query(Localitate.nume_localitate.label("city"), pps, cnt)
        .join(Anunt, Anunt.id_localitate == Localitate.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(Anunt.suprafata.isnot(None))
        .filter(Anunt.suprafata > 0)
        .filter(Anunt.pret <= MAX_SANE_PRICE)
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    # minim 5 anunturi ca sa nu iasa medii aiurea la orase mici
    rows = (
        q.group_by(Localitate.nume_localitate)
        .having(func.count() >= 5)
        .order_by(desc("pps"))
        .all()
    )
    return [
        {"city": r.city, "price_per_sqm": round(float(r.pps))}
        for r in rows
    ]


# --- 5. cate anunturi sunt activ/inactiv/modificat ---
@router.get("/status-breakdown")
def status_breakdown(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # iau statusul din cel mai recent istoric al fiecarui anunt
    # (acelasi pattern ca la /api/listings)
    latest_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )

    q = (
        db.query(IstoricAnunt.status_anunt.label("status"), func.count().label("cnt"))
        .join(latest_subq, IstoricAnunt.id_istoric == latest_subq.c.latest_id)
        .join(Anunt, Anunt.id_anunt == IstoricAnunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(IstoricAnunt.status_anunt).all()

    # ma asigur ca sunt toate cele 3 chei (chiar si 0)
    result = {"activ": 0, "inactiv": 0, "modificat": 0}
    for r in rows:
        if r.status in result:
            result[r.status] = r.cnt
    return result


# --- 6. optiunile pt dropdown-uri ---
@router.get("/filter-options")
def filter_options(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    counties = [
        j.nume_judet
        for j in db.query(Judet).order_by(Judet.nume_judet).all()
    ]
    property_types = [
        t.nume_tip
        for t in db.query(TipImobil).order_by(TipImobil.nume_tip).all()
    ]
    transaction_types = [
        t.nume_tranzactie
        for t in db.query(TipTranzactie).order_by(TipTranzactie.nume_tranzactie).all()
    ]

    return {
        "counties": counties,
        "property_types": property_types,
        "transaction_types": transaction_types,
    }
