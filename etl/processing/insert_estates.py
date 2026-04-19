from db.connection import SessionLocal
from etl.processing.cleaner import clean_listing, validate_listing
from sqlalchemy import text


def insert_estates(rezultate: list[dict]):
    if not rezultate:
        return

    session = SessionLocal()

    # curat aici (nu in scraper) ca sa iasa acelasi id_raw pt acelasi anunt de pe site-uri diferite
    rezultate_curate = []

    for anunt_raw in rezultate:
        anunt = clean_listing(anunt_raw)
        if validate_listing(anunt):
            rezultate_curate.append(anunt)
        else:
            print(f"[Skip] Anunt invalid: {anunt.get('URL_anunt')}")

    # daca nu mai am nimic, ies
    if not rezultate_curate:
        print("[DB] Nimic de inserat.")
        session.close()
        return

    # insert
    query = text("""INSERT INTO raw_data (
            id_raw, "URL_anunt", judet, oras, suprafata, etaj,
            perioada_constructie, an_constructie, compartimentare,
            camere, tip_tranzactie, tip_imobiliar, platforma, pret, data, processed, imagini_url
        ) VALUES (
            :id_raw, :URL_anunt, :judet, :oras, :suprafata, :etaj,
            :perioada_constructie, :an_constructie, :compartimentare,
            :camere, :tip_tranzactie, :tip_imobiliar, :platforma, :pret, :data, :processed, :imagini_url
        )
        ON CONFLICT (id_raw) DO NOTHING;
    """)

    try:
        session.execute(query, rezultate_curate)
        session.commit()
        print(f"[DB] Gata. {len(rezultate_curate)} anunturi noi inserate, duplicatele ignorate.")
    except Exception as e:
        session.rollback()
        print(f"[DB] Eroare: {e}")
    finally:
        session.close()
