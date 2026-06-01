# uvicorn backend.main:app --reload

import os
from datetime import datetime, timezone
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
    CriteriiCautare,
    Favorite,
    ImagineAnunt,
    IstoricAnunt,
    Judet,
    Localitate,
    PerioadaAnConstructie,
    Estate,
    TipImobil,
    TipTranzactie,
)
from backend.schemas import (
    CriteriiOut,
    CriteriiUpsert,
    LoginRequest,
    RegisterRequest,
    UserOut,
)
from backend.auth import (
    COOKIE_NAME,
    JWT_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.routers.stats_router import router as stats_router
from backend.routers.ml_router import router as ml_router
from backend.routers.admin_router import router as admin_router

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
# panoul de admin
app.include_router(admin_router)


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

    # blocaj pt useri dezactivati de admin (soft-delete)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contul tau a fost dezactivat.",
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


@app.post("/api/auth/register")
def register(
    payload: RegisterRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    # curat spatiile si fac email lowercase ca sa nu am duplicate cu majuscule
    username = payload.username.strip()
    email = payload.email.strip().lower()
    password = payload.password

    # validari simple
    if len(username) < 3 or len(username) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be between 3 and 100 characters",
        )
    if "@" not in email or "." not in email or len(email) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email",
        )
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    # verific daca exista deja - separat ca sa pot da mesaj specific
    if db.query(AppUser).filter(AppUser.username == username).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    if db.query(AppUser).filter(AppUser.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # creez userul - role mereu "user", niciodata admin de aici
    new_user = AppUser(
        username=username,
        email=email,
        password_hash=hash_password(password),
        role="user",
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # login automat - acelasi cookie ca la /login
    token = create_access_token(user_id=new_user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=JWT_EXPIRE_MINUTES * 60,
        path="/",
    )

    return {"user": UserOut.model_validate(new_user)}


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


# helper-e pt listings - le folosesc si la /api/listings si la /api/favorites


def _build_listings_base_query(db: Session):
    # query-ul mare cu toate join-urile, fara filtre - le adaug separat dupa apel
    # iau cel mai nou istoric pt fiecare anunt (id_istoric autoincrement, deci max = ultimul)
    latest_istoric_subq = (
        db.query(
            IstoricAnunt.id_anunt.label("id_anunt"),
            func.max(IstoricAnunt.id_istoric).label("latest_id"),
        )
        .group_by(IstoricAnunt.id_anunt)
        .subquery()
    )

    # outer join la tabelele de lookup ca sa nu pierd anunturi daca lipseste ceva
    return (
        db.query(
            Anunt.id_anunt,
            Anunt.pret,
            Anunt.suprafata,
            Anunt.etaj,
            Anunt.an_constructie,
            Anunt.data_publicare,
            Anunt.compartimentare.label("compartimentare_raw"),
            Anunt.id_compartimentare,
            Anunt.id_tip_imobiliar,
            Anunt.camere,
            IstoricAnunt.status_anunt,
            Judet.nume_judet,
            Localitate.nume_localitate,
            TipImobil.nume_tip,
            TipTranzactie.nume_tranzactie,
            PerioadaAnConstructie.perioada_constructie,
            Compartimentare.nume_compartimentare,
            Estate.URL_anunt,
            Estate.platforma,
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


def _serialize_listing_rows(db: Session, rows, current_user_id: int) -> list[dict]:
    # primesc rândurile dintr-un query construit cu _build_listings_base_query
    # si le transform in dict-uri pt frontend, atasand imaginile si is_favorite
    ids_anunturi = [r.id_anunt for r in rows]

    # imaginile - intr-un singur query ca sa nu fac N+1
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

    # favoritele user-ului curent dintre anunturile din pagina asta
    favorite_ids = set()
    if ids_anunturi:
        fav_rows = (
            db.query(Favorite.id_anunt)
            .filter(Favorite.id_user == current_user_id)
            .filter(Favorite.id_anunt.in_(ids_anunturi))
            .all()
        )
        favorite_ids = {r.id_anunt for r in fav_rows}

    items = []
    for r in rows:
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
            # id-uri pe care le folosesc sa prefilez dropdown-urile din modalul
            # de edit (admin)
            "id_compartimentare": r.id_compartimentare,
            "id_tip_imobiliar": r.id_tip_imobiliar,
            "platforma": r.platforma,
            "camere": r.camere,
            "url_anunt": r.URL_anunt,
            "imagini": imagini_by_anunt.get(r.id_anunt, []),
            "is_favorite": r.id_anunt in favorite_ids,
        })
    return items


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
    camere: Optional[int] = None,
    # paginare
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    q = _build_listings_base_query(db)

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
    if camere is not None:
        # camere e int pe anunturi (dupa normalizare) anunturile fara camere setate (NULL) sunt excluse cand filtrul e activ
        q = q.filter(Anunt.camere == camere)
    # arat doar anunturile active, restul nu mai apar deloc in listings
    q = q.filter(IstoricAnunt.status_anunt == "activ")

    total = q.count()

    offset = (page - 1) * page_size
    rows = (
        q.order_by(Anunt.data_publicare.desc().nullslast(), Anunt.id_anunt.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = _serialize_listing_rows(db, rows, current_user.id)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


# --- favorites ---


@app.get("/api/favorites")
def list_favorites(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):

    q = (
        _build_listings_base_query(db)
        .join(Favorite, Favorite.id_anunt == Anunt.id_anunt)
        .filter(Favorite.id_user == current_user.id)
    )

    total = q.count()

    offset = (page - 1) * page_size
    rows = (
        q.order_by(Anunt.id_anunt.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = _serialize_listing_rows(db, rows, current_user.id)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


@app.post("/api/favorites/{id_anunt}")
def add_favorite(
    id_anunt: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    # verific ca anuntul exista (ca sa nu primesc FK violation)
    anunt = db.query(Anunt).filter(Anunt.id_anunt == id_anunt).first()
    if anunt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anunt not found",
        )

    # daca e deja la favorite nu fac nimic (idempotent)
    existing = db.query(Favorite).filter(
        Favorite.id_user == current_user.id,
        Favorite.id_anunt == id_anunt,
    ).first()
    if existing is not None:
        return {"message": "Already favorited"}

    fav = Favorite(
        id_user=current_user.id,
        id_anunt=id_anunt,
        created_at=datetime.now(timezone.utc),
    )
    db.add(fav)
    db.commit()
    return {"message": "Favorited"}


@app.delete("/api/favorites/{id_anunt}")
def remove_favorite(
    id_anunt: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    fav = db.query(Favorite).filter(
        Favorite.id_user == current_user.id,
        Favorite.id_anunt == id_anunt,
    ).first()
    if fav is None:
        # nu dau eroare - daca nu e la favorite, nu e nimic de scos
        return {"message": "Not favorited"}

    db.delete(fav)
    db.commit()
    return {"message": "Removed"}


# --- criterii notificari ---


@app.get("/api/me/criterii", response_model=Optional[CriteriiOut])
def get_my_criterii(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    # userul are un singur profil, deci .first() returneaza ori randul, ori None
    # daca e None inseamna ca nu s-a setat inca nimic (cont nou)
    crit = db.query(CriteriiCautare).filter(
        CriteriiCautare.id_user == current_user.id
    ).first()
    return crit


@app.put("/api/me/criterii", response_model=CriteriiOut)
def upsert_my_criterii(
    payload: CriteriiUpsert,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(get_current_user),
):
    # se verifica daca userul are deja un profil salvat
    # daca da -> update, daca nu -> insert nou (upsert manual)
    crit = db.query(CriteriiCautare).filter(
        CriteriiCautare.id_user == current_user.id
    ).first()

    if crit is None:
        crit = CriteriiCautare(
            id_user=current_user.id,
            created_at=datetime.now(timezone.utc),
        )
        db.add(crit)

    # se suprascriu toate campurile cu ce a trimis frontend-ul, inclusiv null-urile
    # daca userul a sters un filtru (l-a pus pe "Orice") trebuie sa devina null in DB
    crit.id_judet = payload.id_judet
    crit.id_localitate = payload.id_localitate
    crit.id_tip_imobiliar = payload.id_tip_imobiliar
    crit.id_tip_tranzactie = payload.id_tip_tranzactie
    crit.id_compartimentare = payload.id_compartimentare
    crit.pret_min = payload.pret_min
    crit.pret_max = payload.pret_max
    crit.suprafata_min = payload.suprafata_min
    crit.suprafata_max = payload.suprafata_max
    crit.camere = payload.camere
    crit.activ = payload.activ

    db.commit()
    # refresh ca sa iau valorile salvate (cu id-ul autoincrement, created_at etc)
    db.refresh(crit)
    return crit
