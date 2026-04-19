# aleg modelul bun in functie de tip si tranzactie si dau predictia

import os

import joblib
import pandas as pd
from fastapi import HTTPException

from backend.ml.train import (
    COLS_APARTAMENT_INCHIRIERE_PATH,
    COLS_APARTAMENT_VANZARE_PATH,
    COLS_CASA_VANZARE_PATH,
    RF_APARTAMENT_INCHIRIERE_PATH,
    RF_APARTAMENT_VANZARE_PATH,
    RF_CASA_VANZARE_PATH,
)

# (tip, tranzactie) -> (model, coloane, cheie)
MODEL_MAP = {
    ("Apartament", "vanzare"): (
        RF_APARTAMENT_VANZARE_PATH,
        COLS_APARTAMENT_VANZARE_PATH,
        "apartament_vanzare",
    ),
    ("Casa", "vanzare"): (
        RF_CASA_VANZARE_PATH,
        COLS_CASA_VANZARE_PATH,
        "casa_vanzare",
    ),
    ("Apartament", "inchiriere"): (
        RF_APARTAMENT_INCHIRIERE_PATH,
        COLS_APARTAMENT_INCHIRIERE_PATH,
        "apartament_inchiriere",
    ),
}


def _all_models_exist() -> bool:
    # toate cele 3 modele si listele lor de coloane trebuie sa fie pe disc
    for model_path, cols_path, _ in MODEL_MAP.values():
        if not os.path.exists(model_path) or not os.path.exists(cols_path):
            return False
    return True


def predict_price(input_data: dict) -> dict:
    # primesc un dict cu date si intorc pretul estimat

    if not _all_models_exist():
        raise HTTPException(
            status_code=400,
            detail="Models have not been trained yet. Please retrain first.",
        )

    # 1. aleg modelul dupa combinatia tip + tranzactie
    key = (input_data.get("property_type"), input_data.get("transaction_type"))
    if key not in MODEL_MAP:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Nu exista model pentru combinatia {key}. "
                "Combinatii valide: Apartament+vanzare, Casa+vanzare, Apartament+inchiriere."
            ),
        )

    model_path, cols_path, model_key = MODEL_MAP[key]

    # 2. incarc modelul si coloanele
    model = joblib.load(model_path)
    feature_columns = joblib.load(cols_path)

    # 3. pun inputul intr-un DataFrame de un rand
    df = pd.DataFrame([input_data])

    # daca n-a trimis localitate, ii pun "alta"
    if "locality" not in df.columns or pd.isna(df.at[0, "locality"]) or df.at[0, "locality"] == "":
        df["locality"] = "alta"

    # scot property_type si transaction_type - modelul e deja specializat
    df = df.drop(columns=["property_type", "transaction_type"], errors="ignore")

    # 4. one-hot pe aceleasi coloane ca la antrenare
    df_encoded = pd.get_dummies(df, columns=["county", "locality"])

    # 5. aliniez coloanele cu cele de la antrenare
    df_aligned = df_encoded.reindex(columns=feature_columns, fill_value=0)

    # 6. predictie
    pred = model.predict(df_aligned)[0]

    return {
        "model_type": input_data["property_type"],
        "transaction_type": input_data["transaction_type"],
        "price": round(float(pred)),
    }
