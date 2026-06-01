# iau datele din DB pt antrenare
# intorc un DataFrame cu un rand pt fiecare anunt

import pandas as pd
from sqlalchemy.orm import Session

from db.models import Anunt, Estate, Judet, Localitate, TipImobil, TipTranzactie


def _to_int_or_zero(value):
    # daca nu pot transforma in int pun 0
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _etaj_to_int(value):
    # parterul e 0, asa ca etajul lipsa il pun -1
    if value is None:
        return -1
    try:
        return int(value)
    except (ValueError, TypeError):
        return -1


def load_training_data(db: Session) -> pd.DataFrame:
    # iau doar pretul curent din anunturi, nu istoric
    # minim: pret sa nu fie null si suprafata > 0

    rows = (
        db.query(
            Anunt.pret.label("pret"),
            Anunt.suprafata.label("suprafata"),
            Anunt.etaj.label("etaj"),
            Anunt.an_constructie.label("an_constructie"),
            Anunt.camere.label("camere"),
            Judet.nume_judet.label("county"),
            Localitate.nume_localitate.label("locality"),
            TipImobil.nume_tip.label("property_type"),
            TipTranzactie.nume_tranzactie.label("transaction_type"),
        )
        .join(Localitate, Localitate.id_localitate == Anunt.id_localitate)
        .join(Judet, Judet.id_judet == Localitate.id_judet)
        .outerjoin(TipImobil, TipImobil.id_tip_imobiliar == Anunt.id_tip_imobiliar)
        .join(
            TipTranzactie, TipTranzactie.id_tip_tranzactie == Anunt.id_tip_tranzactie
        )
        .join(Estate, Estate.id_raw == Anunt.id_sursa_raw)
        .filter(Anunt.pret.isnot(None))
        .filter(Anunt.suprafata.isnot(None))
        .filter(Anunt.suprafata > 0)
        # doar Storia si imobiliare.ro (OLX nu are an_constructie si e putin)
        .filter(Estate.platforma.in_(["Storia", "imobiliare.ro"]))
        # nu filtrez vanzare aici, antrenez modele separate pe tip si tranzactie
        .all()
    )

    # fac cate un dict pt fiecare rand, apoi DataFrame
    data = []
    for r in rows:
        data.append(
            {
                "pret": r.pret,
                "suprafata": r.suprafata,
                # astea sunt string in DB, le fac int sau 0
                "etaj": _etaj_to_int(r.etaj),
                "an_constructie": _to_int_or_zero(r.an_constructie),
                "camere": _to_int_or_zero(r.camere),
                # pe celelalte le las string, fac get_dummies mai jos
                # daca sunt None pun "necunoscut" ca sa nu crape
                "county": r.county or "necunoscut",
                "locality": r.locality or "necunoscut",
                "property_type": r.property_type or "necunoscut",
                "transaction_type": r.transaction_type or "necunoscut",
            }
        )

    return pd.DataFrame(data)
