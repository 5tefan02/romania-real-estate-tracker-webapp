# rutele pt pagina de Statistics
# toate cer login si pot avea filtre: county / transaction_type / property_type

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import (
    Anunt,
    AppUser,
    Compartimentare,
    Estate,
    IstoricAnunt,
    Judet,
    Localitate,
    PerioadaAnConstructie,
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


def _active_anunt_ids(db: Session):
    # subquery cu id-urile anunturilor active
    # = ultima inregistrare din istoric are status_anunt = 'activ'
    # se folosesc cu .join(...) pe Anunt.id_anunt pe statisticile de "piata curenta"
    latest_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )
    return (
        db.query(IstoricAnunt.id_anunt.label("id_anunt"))
        .join(latest_subq, IstoricAnunt.id_istoric == latest_subq.c.latest_id)
        .filter(IstoricAnunt.status_anunt == "activ")
        .subquery()
    )


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

    # iau media pretului pe saptamana, dupa data din istoric
    # IYYY = an ISO, IW = saptamana ISO (01-53)
    # format ex: "2026-W21"
    week_col = func.to_char(IstoricAnunt.data_inceput, 'IYYY-"W"IW').label("week")

    q = (
        db.query(
            week_col,
            # folosesc mediana in loc de medie ca sa nu fie influentata de outlieri
            # (ex: o chirie de 15000 EUR/luna intr-o saptamana cu 5 anunturi normale
            # ar duce media la cateva mii; mediana ramane in zona reala)
            func.percentile_cont(0.5).within_group(IstoricAnunt.pret.asc()).label("avg_price"),
        )
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

    rows = q.group_by(week_col).order_by(week_col).all()
    return [
        {"week": r.week, "pret mediu": round(float(r.avg_price))}
        for r in rows
        if r.avg_price is not None
    ]


# cate bucket-uri fac pe axa X
NUM_BUCKETS = 25


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

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)

    # intai iau min si max ca sa fac bucket-urile pe intervalul real
    base = (
        db.query(Anunt)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
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

    # percentila 5 jos si 99 sus
    # pe partea de jos taiem doar 5% (preturi prea mici, probabil teren ieftin)
    # pe partea de sus taiem doar 1% (extremele de tip 5M+ care strica scara)
    # asa avem o plaja vizibila cat mai larga fara sa ne strice un outlier extrem
    mn_pct, mx_pct = base.with_entities(
        func.percentile_cont(0.05).within_group(Anunt.pret.asc()),
        func.percentile_cont(0.99).within_group(Anunt.pret.asc()),
    ).one()

    if mn_pct is None or mx_pct is None:
        return []

    mn = int(mn_pct)
    mx = int(mx_pct)

    # daca toate sunt la fel fac un singur bucket
    if mn == mx:
        cnt = base.with_entities(func.count()).scalar() or 0
        return [{"range": _format_price_label(mn), "count": cnt}]

    # bucketing linear pe intervalul [p5, p95]
    # intervalele sunt egale ca lungime in EUR ca sa fie usor de citit
    # ("50k-100k" = exact 50000 EUR latime, indiferent de bucket)
    # outlierii peste/sub plaja se adauga in primul/ultimul bucket
    bucket_col = func.width_bucket(Anunt.pret, mn, mx, NUM_BUCKETS).label("b")

    q = base.with_entities(bucket_col, func.count().label("count")).group_by(bucket_col)
    rows = q.all()
    counts = {int(r.b): r.count for r in rows}

    # NU mai absorb outlierii in bucket-urile de capat (sub p5 si peste p99)
    # altfel ultimul bucket apare disproportionat de mare
    # anunturile din extreme nu apar deloc pe grafic (~6% din total - acceptabil)
    step = (mx - mn) / NUM_BUCKETS
    result = []
    for i in range(1, NUM_BUCKETS + 1):
        lo = mn + step * (i - 1)
        hi = mn + step * i
        label = f"{_format_price_label(lo)}-{_format_price_label(hi)}"
        count = counts.get(i, 0)
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

    # pretul mediu pe mp = total bani / total suprafata (pe oras)
    # NU AVG(pret/suprafata) - aia e mean of ratios si e biased
    # (un apartament mic scump trage media in sus disproportionat)
    # varianta corecta da fiecarui mp ponderea lui in calcul
    # *1.0 ca sa nu faca impartire intreaga
    pps = (func.sum(Anunt.pret) * 1.0 / func.sum(Anunt.suprafata)).label("pps")
    cnt = func.count().label("cnt")

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)

    q = (
        db.query(Localitate.nume_localitate.label("city"), pps, cnt)
        .join(Anunt, Anunt.id_localitate == Localitate.id_localitate)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
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


# --- 6. distributia pe nr de camere ---
@router.get("/rooms-distribution")
def rooms_distribution(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # grupez pe nr de camere, ignor anunturile fara info despre asta
    # pun "5+" la toate care au 5 sau mai multe ca sa nu fie 10-15 categorii separate
    # bucketing-ul il fac in Python (mai usor decat case in SQL)
    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)
    q = (
        db.query(Anunt.camere.label("camere"), func.count().label("cnt"))
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(Anunt.camere.isnot(None))
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(Anunt.camere).order_by(Anunt.camere).all()

    # pun in 5 buckets fixe: 1, 2, 3, 4, 5+
    buckets = {"1": 0, "2": 0, "3": 0, "4": 0, "5+": 0}
    for r in rows:
        if r.camere is None:
            continue
        if r.camere >= 5:
            buckets["5+"] += r.cnt
        elif 1 <= r.camere <= 4:
            buckets[str(r.camere)] += r.cnt

    return [{"rooms": k, "count": v} for k, v in buckets.items()]


# --- 7. distributia pe perioada constructiei ---
@router.get("/period-distribution")
def period_distribution(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)
    q = (
        db.query(
            PerioadaAnConstructie.perioada_constructie.label("period"),
            func.count().label("cnt"),
        )
        .join(Anunt, Anunt.id_perioada_constructie == PerioadaAnConstructie.id_an_constructie)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(PerioadaAnConstructie.perioada_constructie).all()
    return [{"period": r.period, "count": r.cnt} for r in rows]


# --- 8. distributia pe compartimentare ---
@router.get("/compartment-distribution")
def compartment_distribution(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)
    q = (
        db.query(
            Compartimentare.nume_compartimentare.label("compartment"),
            func.count().label("cnt"),
        )
        .join(Anunt, Anunt.id_compartimentare == Compartimentare.id_compartimentare)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.group_by(Compartimentare.nume_compartimentare).all()
    return [{"compartment": r.compartment, "count": r.cnt} for r in rows]


# --- 9. top 10 orase dupa nr anunturi active ---
@router.get("/top-cities")
def top_cities(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # iau cel mai recent istoric pt fiecare anunt ca sa stiu daca e activ
    latest_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )

    q = (
        db.query(Localitate.nume_localitate.label("city"), func.count().label("cnt"))
        .join(Anunt, Anunt.id_localitate == Localitate.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .join(latest_subq, latest_subq.c.id_anunt == Anunt.id_anunt)
        .join(IstoricAnunt, IstoricAnunt.id_istoric == latest_subq.c.latest_id)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(IstoricAnunt.status_anunt == "activ")
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = (
        q.group_by(Localitate.nume_localitate)
        .order_by(desc("cnt"))
        .limit(10)
        .all()
    )
    return [{"city": r.city, "count": r.cnt} for r in rows]


# --- 10. distributia pe suprafata ---
# bucket-uri fixe in mp (pt real estate au sens valori clare)
SURFACE_BUCKETS = [
    (0, 40, "< 40"),
    (40, 60, "40-60"),
    (60, 80, "60-80"),
    (80, 100, "80-100"),
    (100, 150, "100-150"),
    (150, None, "150+"),
]


@router.get("/surface-distribution")
def surface_distribution(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # iau toate suprafetele care trec filtrele, bucketing-ul il fac in Python (e mai clar)
    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)
    q = (
        db.query(Anunt.suprafata)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(Anunt.suprafata.isnot(None))
        .filter(Anunt.suprafata > 0)
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    rows = q.all()

    counts = [0] * len(SURFACE_BUCKETS)
    for r in rows:
        s = r.suprafata
        for i, (lo, hi, _) in enumerate(SURFACE_BUCKETS):
            if hi is None:
                if s >= lo:
                    counts[i] += 1
                    break
            elif lo <= s < hi:
                counts[i] += 1
                break

    return [
        {"range": label, "count": counts[i]}
        for i, (_, _, label) in enumerate(SURFACE_BUCKETS)
    ]


# --- 11. modificari de pret (statistici sumare) ---
@router.get("/price-changes")
def price_changes(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # pasul 1: scot id-urile de anunturi care trec filtrele
    # (fac un query separat ca sa pot folosi rezultatele si la denominator)
    base_q = (
        db.query(Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
    )
    base_q = _apply_filters(base_q, county, transaction_type, property_type)

    total_anunturi = base_q.count()
    if total_anunturi == 0:
        return {
            "total_anunturi": 0,
            "anunturi_cu_modificari": 0,
            "procent_anunturi_cu_modificari": 0,
            "scaderi": 0,
            "cresteri": 0,
            "avg_scadere_pct": 0,
            "avg_crestere_pct": 0,
        }

    # pasul 2: pt fiecare istoric, iau si pretul anterior cu LAG
    # (PARTITION BY id_anunt ORDER BY data_inceput - fereastra pe fiecare anunt sortat in ordine cronologica)
    lag_pret = func.lag(IstoricAnunt.pret).over(
        partition_by=IstoricAnunt.id_anunt,
        order_by=IstoricAnunt.data_inceput,
    ).label("old_price")

    filtered_ids_subq = base_q.subquery()
    inner = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            IstoricAnunt.pret.label("new_price"),
            lag_pret,
        )
        .join(filtered_ids_subq, filtered_ids_subq.c.id_anunt == IstoricAnunt.id_anunt)
        .subquery()
    )

    # iau doar randurile cu pret anterior diferit (modificari reale)
    changes_q = db.query(
        inner.c.id_anunt,
        inner.c.new_price,
        inner.c.old_price,
    ).filter(inner.c.old_price.isnot(None)).filter(inner.c.new_price != inner.c.old_price)

    all_changes = changes_q.all()

    # modificarile reale de pret la imobiliare nu trec de cateva zeci de procente
    # peste +/- 200% e aproape sigur eroare de scraping
    # (ex: scraper-ul a luat la inceput pretul/mp si apoi pretul total al unui teren)
    # daca nu filtrez, un singur outlier strica media
    MAX_REASONABLE_PCT = 200

    scaderi = 0
    cresteri = 0
    suma_scadere_pct = 0.0
    suma_crestere_pct = 0.0
    anunturi_cu_modificari_set = set()

    for ch in all_changes:
        if ch.old_price <= 0:
            # protectie la impartire (n-ar trebui sa apara, pretul e > 0 in toate scenariile reale)
            continue
        diff_pct = (ch.new_price - ch.old_price) * 100.0 / ch.old_price

        # ignor modificarile extreme (erori de date)
        if abs(diff_pct) > MAX_REASONABLE_PCT:
            continue

        anunturi_cu_modificari_set.add(ch.id_anunt)
        if diff_pct < 0:
            scaderi += 1
            suma_scadere_pct += diff_pct
        else:
            cresteri += 1
            suma_crestere_pct += diff_pct

    anunturi_cu_modificari = len(anunturi_cu_modificari_set)

    return {
        "total_anunturi": total_anunturi,
        "anunturi_cu_modificari": anunturi_cu_modificari,
        "procent_anunturi_cu_modificari": round(
            anunturi_cu_modificari * 100.0 / total_anunturi, 1
        ),
        "scaderi": scaderi,
        "cresteri": cresteri,
        "avg_scadere_pct": round(suma_scadere_pct / scaderi, 1) if scaderi else 0,
        "avg_crestere_pct": round(suma_crestere_pct / cresteri, 1) if cresteri else 0,
    }


# --- 12. timpul mediu de viata al unui anunt ---
@router.get("/listing-lifetime")
def listing_lifetime(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # iau doar anunturile inactivate (cele active inca ruleaza, nu am o durata finala pt ele)
    # in postgres scaderea de Date intoarce int (nr de zile)
    durata = func.avg(IstoricAnunt.data_sfarsit - IstoricAnunt.data_inceput).label("avg_days")

    q = (
        db.query(durata, func.count().label("cnt"))
        .join(Anunt, Anunt.id_anunt == IstoricAnunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(IstoricAnunt.status_anunt == "inactiv")
        .filter(IstoricAnunt.data_sfarsit.isnot(None))
    )
    q = _apply_filters(q, county, transaction_type, property_type)

    row = q.one()
    avg_days = round(float(row.avg_days), 1) if row.avg_days is not None else 0
    return {"avg_days": avg_days, "count": row.cnt}


# --- 13. top 5 si bottom 5 judete dupa pret mediu ---
@router.get("/top-bottom-counties")
def top_bottom_counties(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    avg_price = func.avg(Anunt.pret).label("avg_price")

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)

    base = (
        db.query(Judet.nume_judet.label("county"), avg_price)
        .join(Localitate, Localitate.id_judet == Judet.id_judet)
        .join(Anunt, Anunt.id_localitate == Localitate.id_localitate)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
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

    # cer cel putin 10 anunturi per judet ca sa nu iasa medii aiurea
    grouped = base.group_by(Judet.nume_judet).having(func.count() >= 10)

    top = grouped.order_by(desc("avg_price")).limit(5).all()
    bottom = grouped.order_by(asc("avg_price")).limit(5).all()

    return {
        "top": [{"county": r.county, "avg_price": round(float(r.avg_price))} for r in top],
        "bottom": [{"county": r.county, "avg_price": round(float(r.avg_price))} for r in bottom],
    }


# --- 14. scatter suprafata vs pret ---
# limita ca sa nu trimit prea multe puncte la browser (recharts incepe sa lag la 5k+)
SCATTER_MAX_POINTS = 1500


@router.get("/surface-vs-price")
def surface_vs_price(
    county: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    property_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    _validate_filters(db, county, transaction_type, property_type)

    # doar anunturi active (snapshot al pietei curente)
    active_subq = _active_anunt_ids(db)

    base = (
        db.query(Anunt.suprafata, Anunt.pret)
        .join(active_subq, active_subq.c.id_anunt == Anunt.id_anunt)
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .outerjoin(
            TipTranzactie,
            TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie,
        )
        .filter(Anunt.suprafata.isnot(None))
        .filter(Anunt.suprafata > 0)
        .filter(Anunt.pret.isnot(None))
        .filter(Anunt.pret > 0)
        .filter(Anunt.pret <= MAX_SANE_PRICE)
    )
    base = _apply_filters(base, county, transaction_type, property_type)

    # scot outlierii de pe suprafata (percentila 99) ca sa nu strice scara
    # ex: un apartament cu 6000mp e clar eroare de scraping, il ignor
    p99 = base.with_entities(
        func.percentile_cont(0.99).within_group(Anunt.suprafata.asc())
    ).scalar()

    if p99 is not None:
        base = base.filter(Anunt.suprafata <= p99)

    # random() ca sa iau un esantion reprezentativ, nu doar primele
    rows = base.order_by(func.random()).limit(SCATTER_MAX_POINTS).all()
    return [{"surface": r.suprafata, "price": r.pret} for r in rows]


# --- 15. optiunile pt dropdown-uri ---
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
