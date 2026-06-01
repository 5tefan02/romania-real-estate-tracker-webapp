# aici tin toate rutele pentru panoul de admin
# toate cer rol "admin" prin dependency-ul require_admin din auth.py

from datetime import date, timedelta
from threading import Thread

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.auth import require_admin
from backend.schemas import AdminListingUpdate, AdminUserOut
from db.connection import get_db
from db.models import (
    Anunt,
    AppUser,
    CriteriiCautare,
    IstoricAnunt,
    NotificareTrimisa,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])


# starea ETL-ului o tin direct in memorie, intr-un dict cu o singura cheie
# nu am o tabela in DB pt asta - vreau sa pastrez baza de date curata
# la restart de backend flag-ul se reseteaza, dar asta nu e o problema:
# inseamna ca daca ETL-ul rula cand am restartat, thread-ul s-a oprit (daemon=True)
# si flag-ul revine la False automat - nu raman cu running blocat pe true
_etl_state = {"running": False}


# functia care chiar ruleaza ETL-ul intr-un thread separat
# se apeleaza de POST /etl/run prin Thread(target=_run_etl_in_thread)
# cand se termina (cu sau fara eroare) marchez running=False
def _run_etl_in_thread():
    # import aici, nu sus, ca sa nu trag tot ETL-ul cand pornesc backend-ul
    # (etl/main.py importa scraperele care la randul lor importa selenium etc)
    from etl.main import main as run_etl_main

    try:
        run_etl_main()
    except Exception as e:
        # daca pica ETL-ul nu vreau sa pice si backend-ul
        # afisez eroarea in consola ca admin sa vada
        print(f"[ETL] Eroare in thread: {e}")
    finally:
        # indiferent de rezultat marchez ca s-a terminat
        _etl_state["running"] = False


# --- users ---


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # intorc toti userii, ordonati alfabetic dupa username
    # asa e mai usor de gasit cineva specific in tabel
    users = db.query(AppUser).order_by(AppUser.username.asc()).all()
    return users


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # blocaj: admin-ul nu se poate dezactiva pe el insusi
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nu te poti dezactiva pe tine insuti.",
        )

    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilizatorul nu exista.",
        )

    # soft-delete: nu sterg fizic, doar dezactivez contul
    # login-ul si get_current_user resping userii cu is_active=False
    # favoritele, criteriile si notificarile raman intacte (eventual restore)
    user.is_active = False
    db.commit()
    return {"message": "Utilizatorul a fost dezactivat."}


# --- listings ---


@router.patch("/listings/{id_anunt}")
def update_listing(
    id_anunt: int,
    payload: AdminListingUpdate,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # iau anuntul din DB - daca nu exista returnez 404
    anunt = db.query(Anunt).filter(Anunt.id_anunt == id_anunt).first()
    if anunt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuntul nu exista.",
        )

    # campurile de pe Anunt - le suprascriu cu ce a trimis admin-ul
    # (inclusiv cu null daca admin a sters valoarea)
    anunt.pret = payload.pret
    anunt.suprafata = payload.suprafata
    anunt.etaj = payload.etaj
    anunt.id_compartimentare = payload.id_compartimentare
    anunt.id_tip_imobiliar = payload.id_tip_imobiliar
    anunt.camere = payload.camere

    db.commit()
    return {"message": "Anuntul a fost actualizat."}


@router.delete("/listings/{id_anunt}")
def delete_listing(
    id_anunt: int,
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # iau anuntul - daca nu exista returnez 404
    anunt = db.query(Anunt).filter(Anunt.id_anunt == id_anunt).first()
    if anunt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anuntul nu exista.",
        )

    # soft-delete: gasesc istoricul activ si il trec pe inactiv
    # query-ul de listings filtreaza pe status_anunt = 'activ' deci anuntul
    # dispare din pagina, dar ramane in DB cu istoricul intact
    istoric_activ = (
        db.query(IstoricAnunt)
        .filter(IstoricAnunt.id_anunt == id_anunt)
        .filter(IstoricAnunt.status_anunt == "activ")
        .first()
    )

    if istoric_activ:
        istoric_activ.status_anunt = "inactiv"
        istoric_activ.data_sfarsit = date.today()
        db.commit()
        return {"message": "Anuntul a fost dezactivat."}

    # daca nu exista istoric activ (anuntul era deja inactivat) nu am ce face
    return {"message": "Anuntul era deja inactiv."}


# --- etl ---


@router.post("/etl/run")
def etl_run(
    current_user: AppUser = Depends(require_admin),
):
    # daca ruleaza deja nu pornesc o a doua rulare in paralel
    # (ar duce la duplicate la scraping si la mailuri trimise de doua ori)
    if _etl_state["running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ETL-ul ruleaza deja.",
        )

    # marchez ca a pornit inainte sa dau drumul la thread
    _etl_state["running"] = True

    # daemon=True ca threadul sa moara cu procesul daca opresc backend-ul cu Ctrl+C
    thread = Thread(target=_run_etl_in_thread, daemon=True)
    thread.start()

    return {"message": "ETL pornit."}


# --- dashboard / stats ---


@router.get("/stats")
def admin_stats(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # intorc toate KPI-urile pt dashboard intr-un singur JSON
    # asa frontend-ul face un singur fetch in loc de mai multe
    # daca devine prea lent, putem sparge in mai multe endpoint-uri mai tarziu

    # --- useri ---
    users_total = db.query(func.count(AppUser.id)).scalar()
    # useri cu profil de notificari activ
    users_active_profile = (
        db.query(func.count(CriteriiCautare.id))
        .filter(CriteriiCautare.activ == True)
        .scalar()
    )

    # --- anunturi ---
    # doar total si numarul de anunturi noi (azi si in ultima saptamana)
    # detaliile pe status/platforma/judete sunt pe pagina de Statistics, nu aici
    listings_total = db.query(func.count(Anunt.id_anunt)).scalar()

    today = date.today()
    week_ago = today - timedelta(days=7)
    listings_new_today = (
        db.query(func.count(Anunt.id_anunt))
        .filter(Anunt.data_publicare == today)
        .scalar()
    )
    listings_new_week = (
        db.query(func.count(Anunt.id_anunt))
        .filter(Anunt.data_publicare >= week_ago)
        .scalar()
    )

    # --- mailuri trimise ultimele 7 zile (pt line chart) ---
    # grupez pe ziua trimiterii. iau ultimele 7 zile (azi inclusiv = 6 zile in urma)
    seven_days_ago = today - timedelta(days=6)
    email_rows = (
        db.query(
            func.date(NotificareTrimisa.data_trimitere).label("ziua"),
            func.count(),
        )
        .filter(func.date(NotificareTrimisa.data_trimitere) >= seven_days_ago)
        .group_by(func.date(NotificareTrimisa.data_trimitere))
        .order_by("ziua")
        .all()
    )
    emails_by_day_map = {str(d): c for d, c in email_rows}
    # umplu zilele lipsa cu 0 ca sa nu am sarituri in grafic
    emails_last_7_days = []
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        d_str = str(d)
        emails_last_7_days.append(
            {"data": d_str, "count": emails_by_day_map.get(d_str, 0)}
        )

    return {
        "users_total": users_total,
        "users_active_profile": users_active_profile,
        "listings_total": listings_total,
        "listings_new_today": listings_new_today,
        "listings_new_week": listings_new_week,
        "emails_last_7_days": emails_last_7_days,
    }
