# schemele pt pydantic (request/response)
# le tin separate de sqlalchemy ca sa nu ma trezesc ca trimit password-ul la frontend

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    model_config = {"from_attributes": True}


# --- ML ---

class PredictRequest(BaseModel):
    suprafata: int
    etaj: int = 0
    county: str
    locality: Optional[str] = None
    property_type: str
    transaction_type: str
    camere: int = 0
    an_constructie: int = 0


class PredictResponse(BaseModel):
    # intorc tipul si tranzactia ca sa apara corect pe frontend
    model_type: str
    transaction_type: str
    price: int


class PerTypeMetrics(BaseModel):
    training_rows: int
    mae: int
    r2: float


class TrainResponse(BaseModel):
    message: str
    apartament_vanzare: PerTypeMetrics
    casa_vanzare: PerTypeMetrics
    apartament_inchiriere: PerTypeMetrics


class ModelInfoResponse(BaseModel):
    models_trained: bool
    last_trained: Optional[str] = None
    # metricele pt fiecare model - le afisez si pe frontend
    apartament_vanzare: Optional[PerTypeMetrics] = None
    casa_vanzare: Optional[PerTypeMetrics] = None
    apartament_inchiriere: Optional[PerTypeMetrics] = None
