# antrenez 3 modele Random Forest:
# (Apartament vanzare), (Casa vanzare), (Apartament inchiriere)
# se cheama din /api/ml/retrain

import os

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

from backend.ml.data_loader import load_training_data

# salvez modelele langa fisierul asta
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models_saved")

# cate un path pt fiecare combinatie
RF_APARTAMENT_VANZARE_PATH = os.path.join(MODELS_DIR, "rf_apartament_vanzare.pkl")
RF_CASA_VANZARE_PATH = os.path.join(MODELS_DIR, "rf_casa_vanzare.pkl")
RF_APARTAMENT_INCHIRIERE_PATH = os.path.join(MODELS_DIR, "rf_apartament_inchiriere.pkl")

COLS_APARTAMENT_VANZARE_PATH = os.path.join(MODELS_DIR, "cols_apartament_vanzare.pkl")
COLS_CASA_VANZARE_PATH = os.path.join(MODELS_DIR, "cols_casa_vanzare.pkl")
COLS_APARTAMENT_INCHIRIERE_PATH = os.path.join(MODELS_DIR, "cols_apartament_inchiriere.pkl")

LOCALITIES_PATH = os.path.join(MODELS_DIR, "localities_by_county.pkl")
METRICS_PATH = os.path.join(MODELS_DIR, "models_metrics.pkl")

# pt fiecare combinatie pun limite la pret/mp ca sa arunc outlierii
# (la vanzare e pret in EUR, la inchiriere e chirie/luna)
MODEL_CONFIGS = [
    {
        "key": "apartament_vanzare",
        "property_type": "Apartament",
        "transaction_type": "vanzare",
        "pret_per_mp_min": 200,
        "pret_per_mp_max": 8000,
        "model_path": RF_APARTAMENT_VANZARE_PATH,
        "cols_path": COLS_APARTAMENT_VANZARE_PATH,
    },
    {
        "key": "casa_vanzare",
        "property_type": "Casa",
        "transaction_type": "vanzare",
        "pret_per_mp_min": 200,
        "pret_per_mp_max": 8000,
        "model_path": RF_CASA_VANZARE_PATH,
        "cols_path": COLS_CASA_VANZARE_PATH,
    },
    {
        "key": "apartament_inchiriere",
        "property_type": "Apartament",
        "transaction_type": "inchiriere",
        # chiria lunara e mult mai mica, plaja alta
        "pret_per_mp_min": 2,
        "pret_per_mp_max": 50,
        "model_path": RF_APARTAMENT_INCHIRIERE_PATH,
        "cols_path": COLS_APARTAMENT_INCHIRIERE_PATH,
    },
]


def _train_single_model(df_subset: pd.DataFrame) -> tuple:
    # antrenez un singur RandomForest pe un subset
    # intorc (model, coloane, mae, r2, cate randuri)

    # property_type si transaction_type nu mai sunt features (sunt fixe pe subset)
    df_encoded = pd.get_dummies(df_subset, columns=["county", "locality"])

    y = df_encoded["pret"]
    X = df_encoded.drop(columns=["pret", "property_type", "transaction_type"])

    feature_columns = list(X.columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # antrenez pe log(pret) ca sa nu fie dominat de preturile mari
    model = TransformedTargetRegressor(
        regressor=RandomForestRegressor(n_estimators=100, random_state=42),
        func=np.log,
        inverse_func=np.exp,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    return model, feature_columns, mae, r2, len(df_subset)


def train_models(db: Session) -> dict:
    # antrenez cele 3 modele, le salvez si intorc metricele

    # 1. iau datele (contine si vanzari si inchirieri)
    df = load_training_data(db)

    # 2. scot preturile si suprafetele invalide
    df = df[df["pret"] > 0]
    df = df[df["suprafata"] >= 15]
    # scot anunturile fara an de constructie (an_constructie e 0 cand lipseste)
    df = df[df["an_constructie"] != 0]

    # 3. localitatile rare (sub 10 anunturi) le bag in "alta"
    # grupez pe tot df-ul sa am aceeasi impartire la toate modelele
    LOCALITY_MIN_COUNT = 10
    locality_counts = df["locality"].value_counts()
    rare_localities = locality_counts[locality_counts < LOCALITY_MIN_COUNT].index
    df.loc[df["locality"].isin(rare_localities), "locality"] = "alta"
    print(f"[ML] Localitati pastrate: {df['locality'].nunique()} (din {len(locality_counts)})")

    # 4. antrenez cate un model pt fiecare combinatie
    results = {}
    os.makedirs(MODELS_DIR, exist_ok=True)

    for cfg in MODEL_CONFIGS:
        # iau doar randurile pt combinatia asta
        df_subset = df[
            (df["property_type"] == cfg["property_type"])
            & (df["transaction_type"] == cfg["transaction_type"])
        ].copy()

        # scot outlierii pe pret/mp
        df_subset["_pret_per_mp"] = df_subset["pret"] / df_subset["suprafata"]
        df_subset = df_subset[
            df_subset["_pret_per_mp"].between(cfg["pret_per_mp_min"], cfg["pret_per_mp_max"])
        ]
        df_subset = df_subset.drop(columns=["_pret_per_mp"])

        if len(df_subset) < 10:
            raise ValueError(
                f"Nu sunt destule date pt {cfg['key']} ({len(df_subset)} randuri)"
            )

        print(f"[ML] Antrenez {cfg['key']} pe {len(df_subset)} randuri...")
        model, cols, mae, r2, rows = _train_single_model(df_subset)

        joblib.dump(model, cfg["model_path"])
        joblib.dump(cols, cfg["cols_path"])

        results[cfg["key"]] = {
            "training_rows": int(rows),
            "mae": round(float(mae)),
            "r2": round(float(r2), 3),
        }

    # 5. salvez harta cu localitati pe judete (o folosesc pt dropdown)
    localities_by_county = {
        county: sorted(group["locality"].unique().tolist())
        for county, group in df.groupby("county")
    }
    joblib.dump(localities_by_county, LOCALITIES_PATH)

    # 6. salvez metricele (le citeste /model-info si le afiseaza frontendul)
    joblib.dump(results, METRICS_PATH)

    return results
