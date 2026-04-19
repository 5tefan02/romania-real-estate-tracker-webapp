# uvicorn backend.main:app --reload

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import (
    Anunt,
    AppUser,
    Compartimentare,
    ImagineAnunt,
    IstoricAnunt,
    Judet,
    Localitate,
    PerioadaAnConstructie,
    Estate,
    TipImobil,
    TipTranzactie,
)
from backend.schemas import LoginRequest, UserOut
from backend.auth import (
    COOKIE_NAME,
    JWT_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    verify_password,
)
from backend.routers.stats_router import router as stats_router
from backend.routers.ml_router import router as ml_router

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

app = FastAPI(title="Real Estate Web API")

# CORS - reactul e pe alt port, trebuie sa il las sa intre
# allow_credentials pe true altfel nu merg cookie urile
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# pun rutele de la Statistics
app.include_router(stats_router)
# pun si rutele de la Predictions
app.include_router(ml_router)


# --- auth ---

@app.post("/api/auth/login")
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    user = db.query(AppUser).filter(AppUser.username == payload.username).first()

    # acelasi mesaj la ambele cazuri sa nu afle daca exista userul sau nu
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user_id=user.id)

    # httponly = js nu poate citi cookie-ul
    # secure = false pt localhost, pe https trebuie true
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=JWT_EXPIRE_MINUTES * 60,
        path="/",
    )

    return {"user": UserOut.model_validate(user)}


@app.post("/api/auth/logout")
def logout(response: Response):
    # doar sterg cookie-ul
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@app.get("/api/auth/me", response_model=UserOut)
def me(current_user: AppUser = Depends(get_current_user)):
    return current_user


@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- listings ---

@app.get("/api/filters")
def get_filter_options(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    # tot ce ii trebuie frontendului pt dropdown-uri dintr-un singur request
    judete = db.query(Judet).order_by(Judet.nume_judet).all()
    localitati = db.query(Localitate).order_by(Localitate.nume_localitate).all()
    tipuri_imobil = db.query(TipImobil).order_by(TipImobil.nume_tip).all()
    tipuri_tranzactie = db.query(TipTranzactie).order_by(TipTranzactie.nume_tranzactie).all()
    compartimentari = db.query(Compartimentare).order_by(Compartimentare.nume_compartimentare).all()

    return {
        "judete": [
            {"id": j.id_judet, "nume": j.nume_judet} for j in judete
        ],
        "localitati": [
            {"id": l.id_localitate, "id_judet": l.id_judet, "nume": l.nume_localitate}
            for l in localitati
        ],
        "tipuri_imobil": [
            {"id": t.id_tip_imobiliar, "nume": t.nume_tip} for t in tipuri_imobil
        ],
        "tipuri_tranzactie": [
            {"id": t.id_tip_tranzactie, "nume": t.nume_tranzactie} for t in tipuri_tranzactie
        ],
        "compartimentari": [
            {"id": c.id_compartimentare, "nume": c.nume_compartimentare}
            for c in compartimentari
        ],
    }


@app.get("/api/listings")
def list_listings(
    # filtre
    judet_id: Optional[int] = None,
    localitate_id: Optional[int] = None,
    tip_imobiliar_id: Optional[int] = None,
    tip_tranzactie_id: Optional[int] = None,
    compartimentare_id: Optional[int] = None,
    pret_min: Optional[int] = None,
    pret_max: Optional[int] = None,
    suprafata_min: Optional[int] = None,
    suprafata_max: Optional[int] = None,
    status_anunt: Optional[str] = None,
    # paginare
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):

    # iau cel mai nou istoric pt fiecare anunt
    # id_istoric e autoincrement asa ca max inseamna ultimul
    latest_istoric_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )

    # query mare - iau coloanele unele cate unele ca sa fac dict mai jos
    # outer join la tabelele de lookup sa nu pierd anunturi daca lipseste ceva
    q = (
        db.query(
            Anunt.id_anunt,
            Anunt.pret,
            Anunt.suprafata,
            Anunt.etaj,
            Anunt.an_constructie,
            Anunt.data_publicare,
            Anunt.compartimentare.label("compartimentare_raw"),
            IstoricAnunt.status_anunt,
            Judet.nume_judet,
            Localitate.nume_localitate,
            TipImobil.nume_tip,
            TipTranzactie.nume_tranzactie,
            PerioadaAnConstructie.perioada_constructie,
            Compartimentare.nume_compartimentare,
            Estate.URL_anunt,
            Estate.platforma,
            Estate.camere,
        )
        .join(latest_istoric_subq, Anunt.id_anunt == latest_istoric_subq.c.id_anunt)
        .join(IstoricAnunt, IstoricAnunt.id_istoric == latest_istoric_subq.c.latest_id)
        .join(Localitate, Anunt.id_localitate == Localitate.id_localitate)
        .join(Judet, Localitate.id_judet == Judet.id_judet)
        .outerjoin(TipImobil, Anunt.id_tip_imobiliar == TipImobil.id_tip_imobiliar)
        .outerjoin(TipTranzactie, Anunt.id_tip_tranzactie == TipTranzactie.id_tip_tranzactie)
        .outerjoin(
            PerioadaAnConstructie,
            Anunt.id_perioada_constructie == PerioadaAnConstructie.id_an_constructie,
        )
        .outerjoin(
            Compartimentare,
            Anunt.id_compartimentare == Compartimentare.id_compartimentare,
        )
        .outerjoin(Estate, Anunt.id_sursa_raw == Estate.id_raw)
    )

    # pun filtrele doar daca au valoare
    if judet_id is not None:
        q = q.filter(Localitate.id_judet == judet_id)
    if localitate_id is not None:
        q = q.filter(Anunt.id_localitate == localitate_id)
    if tip_imobiliar_id is not None:
        q = q.filter(Anunt.id_tip_imobiliar == tip_imobiliar_id)
    if tip_tranzactie_id is not None:
        q = q.filter(Anunt.id_tip_tranzactie == tip_tranzactie_id)
    if compartimentare_id is not None:
        q = q.filter(Anunt.id_compartimentare == compartimentare_id)
    if pret_min is not None:
        q = q.filter(Anunt.pret >= pret_min)
    if pret_max is not None:
        q = q.filter(Anunt.pret <= pret_max)
    if suprafata_min is not None:
        q = q.filter(Anunt.suprafata >= suprafata_min)
    if suprafata_max is not None:
        q = q.filter(Anunt.suprafata <= suprafata_max)
    if status_anunt:
        q = q.filter(IstoricAnunt.status_anunt == status_anunt)

    total = q.count()

    offset = (page - 1) * page_size
    rows = (
        q.order_by(Anunt.data_publicare.desc().nullslast(), Anunt.id_anunt.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    # iau toate imaginile din pagina asta intr-un singur query ca sa nu fac N+1
    # si le grupez local pe id_anunt, ordonate dupa ordine
    ids_anunturi = [r.id_anunt for r in rows]
    imagini_by_anunt = {}
    if ids_anunturi:
        img_rows = (
            db.query(ImagineAnunt.id_anunt, ImagineAnunt.url_imagine)
            .filter(ImagineAnunt.id_anunt.in_(ids_anunturi))
            .order_by(ImagineAnunt.id_anunt, ImagineAnunt.ordine.asc().nullslast())
            .all()
        )
        for id_a, url in img_rows:
            imagini_by_anunt.setdefault(id_a, []).append(url)

    items = []
    for r in rows:
        imagini = imagini_by_anunt.get(r.id_anunt, [])

        items.append({
            "id": r.id_anunt,
            "pret": r.pret,
            "suprafata": r.suprafata,
            "etaj": r.etaj,
            "an_constructie": r.an_constructie,
            "data_publicare": r.data_publicare.isoformat() if r.data_publicare else None,
            "status": r.status_anunt,
            "judet": r.nume_judet,
            "localitate": r.nume_localitate,
            "tip_imobiliar": r.nume_tip,
            "tip_tranzactie": r.nume_tranzactie,
            "perioada_constructie": r.perioada_constructie,
            # daca nu e in lookup folosesc stringul direct de pe anunt
            "compartimentare": r.nume_compartimentare or r.compartimentare_raw,
            "platforma": r.platforma,
            "camere": r.camere,
            "url_anunt": r.URL_anunt,
            "imagini": imagini,
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
