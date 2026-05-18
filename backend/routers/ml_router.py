# rutele pt pagina de Predictions
# /retrain cere admin, celelalte doar login

import os
from datetime import datetime

import joblib
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_current_user, require_admin
from backend.ml.predict import predict_price
from backend.ml.train import (
    COLS_APARTAMENT_INCHIRIERE_PATH,
    COLS_APARTAMENT_VANZARE_PATH,
    COLS_CASA_VANZARE_PATH,
    LOCALITIES_PATH,
    METRICS_PATH,
    RF_APARTAMENT_INCHIRIERE_PATH,
    RF_APARTAMENT_VANZARE_PATH,
    RF_CASA_VANZARE_PATH,
    train_models,
)
from backend.schemas import (
    ModelInfoResponse,
    PredictRequest,
    PredictResponse,
    TrainResponse,
)
from db.connection import get_db
from db.models import AppUser


router = APIRouter(prefix="/api/ml", tags=["ml"])

# toate fisierele care trebuie sa existe ca sa zic ca modelele sunt antrenate
_ALL_MODEL_FILES = [
    RF_APARTAMENT_VANZARE_PATH,
    COLS_APARTAMENT_VANZARE_PATH,
    RF_CASA_VANZARE_PATH,
    COLS_CASA_VANZARE_PATH,
    RF_APARTAMENT_INCHIRIERE_PATH,
    COLS_APARTAMENT_INCHIRIERE_PATH,
]


@router.post("/retrain", response_model=TrainResponse)
def retrain(
    db: Session = Depends(get_db),
    current_user: AppUser = Depends(require_admin),
):
    # antrenez din nou cele 3 modele (doar admin)
    summary = train_models(db)
    return {"message": "Models trained successfully", **summary}


@router.post("/predict", response_model=PredictResponse)
def predict(
    payload: PredictRequest,
    current_user: AppUser = Depends(get_current_user),
):
    return predict_price(payload.model_dump())


@router.get("/localities")
def get_localities(current_user: AppUser = Depends(get_current_user)):
    # intorc {judet: [localitati]} salvate la ultima antrenare
    if not os.path.exists(LOCALITIES_PATH):
        return {}
    return joblib.load(LOCALITIES_PATH)


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info(current_user: AppUser = Depends(get_current_user)):
    # zice daca modelele exista si cand au fost antrenate ultima oara
    # + metricele lor (le afisez pe frontend)
    all_exist = all(os.path.exists(p) for p in _ALL_MODEL_FILES)

    if not all_exist:
        return {"models_trained": False, "last_trained": None}

    mtime = max(
        os.path.getmtime(RF_APARTAMENT_VANZARE_PATH),
        os.path.getmtime(RF_CASA_VANZARE_PATH),
        os.path.getmtime(RF_APARTAMENT_INCHIRIERE_PATH),
    )
    last_trained = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

    metrics = {}
    if os.path.exists(METRICS_PATH):
        metrics = joblib.load(METRICS_PATH)

    return {
        "models_trained": True,
        "last_trained": last_trained,
        "apartament_vanzare": metrics.get("apartament_vanzare"),
        "casa_vanzare": metrics.get("casa_vanzare"),
        "apartament_inchiriere": metrics.get("apartament_inchiriere"),
    }
