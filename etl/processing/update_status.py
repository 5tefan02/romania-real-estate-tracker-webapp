from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from sqlalchemy import exists
from db.connection import SessionLocal
from db.models import Estate, Anunt, IstoricAnunt
from etl.processing.check_status import verificare_status

NUM_WORKERS = 4  # cate browsere deschid in paralel


def _creeaza_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.page_load_strategy = 'eager'
    return webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)


def verifica_si_actualizeaza_preturi():
    session = SessionLocal()

    # iau anunturile care mai sunt active si au URL
    anunturi_de_verificat = session.query(Anunt, Estate).join(
        Estate, Anunt.id_sursa_raw == Estate.id_raw
    ).filter(
        Estate.URL_anunt.isnot(None),
        ~exists().where(
            (IstoricAnunt.id_anunt == Anunt.id_anunt) &
            (IstoricAnunt.status_anunt == 'inactiv')
        )
    ).all()

    if not anunturi_de_verificat:
        print("Nu am gasit anunturi de verificat.")
        session.close()
        return

    total = len(anunturi_de_verificat)
    print(f"Verific {total} anunturi cu {NUM_WORKERS} browsere.")

    # pornesc driverele
    drivers = []
    for i in range(NUM_WORKERS):
        print(f"Pornesc driverul {i+1}/{NUM_WORKERS}...")
        drivers.append(_creeaza_driver())

    # impart URL-urile pe workeri si retin un dict url -> (anunt, raw)
    url_map = {}
    tasks_per_worker = [[] for _ in range(NUM_WORKERS)]

    for idx, (anunt, raw_data) in enumerate(anunturi_de_verificat):
        worker_id = idx % NUM_WORKERS
        url = raw_data.URL_anunt
        url_map[url] = (anunt, raw_data)
        tasks_per_worker[worker_id].append((url, raw_data.platforma))

    def _worker_verifica(worker_id):
        # fiecare worker are lista lui de URL-uri
        driver = drivers[worker_id]
        rezultate = []
        for url, platforma in tasks_per_worker[worker_id]:
            print(f"[Worker {worker_id+1}] Verific: {url}")
            pret_nou = verificare_status(driver, url, platforma)
            rezultate.append((url, pret_nou))
        return rezultate

    azi = date.today()
    schimbari = 0
    inactivate = 0

    try:
        all_results = []
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = [executor.submit(_worker_verifica, i) for i in range(NUM_WORKERS)]
            for future in as_completed(futures):
                all_results.extend(future.result())

        # scrierea in DB o fac pe main thread
        for url, pret_nou in all_results:
            anunt, raw_data = url_map[url]
            pret_vechi = anunt.pret

            istoric_activ = session.query(IstoricAnunt).filter(
                IstoricAnunt.id_anunt == anunt.id_anunt,
                IstoricAnunt.status_anunt == 'activ'
            ).first()

            # anunt inactiv
            if pret_nou is None:
                if istoric_activ:
                    istoric_activ.status_anunt = 'inactiv'
                    istoric_activ.data_sfarsit = azi
                    inactivate += 1
                    print(f" -> Devenit INACTIV: {url}")
                continue

            if pret_nou == 0:
                if not istoric_activ:
                    istoric_nou = IstoricAnunt(
                        id_anunt=anunt.id_anunt,
                        pret=pret_vechi,
                        status_anunt='activ',
                        data_inceput=azi
                    )
                    session.add(istoric_nou)
                continue

            if pret_nou != pret_vechi:
                print(f" -> PRET SCHIMBAT: {url} | Vechi: {pret_vechi} | Nou: {pret_nou}")

                anunt.pret = pret_nou

                if istoric_activ:
                    istoric_activ.data_sfarsit = azi
                    istoric_activ.status_anunt = 'modificat'

                istoric_nou = IstoricAnunt(
                    id_anunt=anunt.id_anunt,
                    pret=pret_nou,
                    status_anunt='activ',
                    data_inceput=azi,
                    data_sfarsit=None
                )
                session.add(istoric_nou)
                schimbari += 1

            elif not istoric_activ:
                istoric_nou = IstoricAnunt(
                    id_anunt=anunt.id_anunt,
                    pret=pret_vechi,
                    status_anunt='activ',
                    data_inceput=azi
                )
                session.add(istoric_nou)

        session.commit()
        print(f"\nGata! {schimbari} preturi modificate, {inactivate} anunturi inactivate.")

    except Exception as e:
        session.rollback()
        print(f"Eroare: {e}")
    finally:
        for d in drivers:
            d.quit()
        session.close()
