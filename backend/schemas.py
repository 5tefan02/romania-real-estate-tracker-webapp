# schemele pt pydantic (request/response)
# le tin separate de sqlalchemy ca sa nu trimit password-ul la frontend

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class AdminUserOut(BaseModel):
    # ca UserOut dar cu created_at - pt tabelul de admin
    id: int
    username: str
    email: str
    role: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminListingUpdate(BaseModel):
    # payload-ul trimis de admin cand editeaza un anunt
    # toate campurile sunt optionale - frontend-ul trimite mereu toate dar
    # le poate trimite null daca admin-ul a sters valoarea din formular
    pret: Optional[int] = None
    suprafata: Optional[int] = None
    etaj: Optional[str] = None
    id_compartimentare: Optional[int] = None
    camere: Optional[int] = None


# --- criterii notificari ---

class CriteriiOut(BaseModel):
    # se trimite la frontend cand userul intra pe pagina de profil
    # ca sa vada filtrele setate anterior
    id_judet: Optional[int] = None
    id_localitate: Optional[int] = None
    id_tip_imobiliar: Optional[int] = None
    id_tip_tranzactie: Optional[int] = None
    id_compartimentare: Optional[int] = None
    pret_min: Optional[int] = None
    pret_max: Optional[int] = None
    suprafata_min: Optional[int] = None
    suprafata_max: Optional[int] = None
    camere: Optional[int] = None
    activ: bool = True

    model_config = {"from_attributes": True}


class CriteriiUpsert(BaseModel):
    # se primeste de la frontend cand userul apasa pe Salveaza
    # toate campurile sunt optionale - daca lipseste = "orice", se salveaza null
    id_judet: Optional[int] = None
    id_localitate: Optional[int] = None
    id_tip_imobiliar: Optional[int] = None
    id_tip_tranzactie: Optional[int] = None
    id_compartimentare: Optional[int] = None
    pret_min: Optional[int] = None
    pret_max: Optional[int] = None
    suprafata_min: Optional[int] = None
    suprafata_max: Optional[int] = None
    camere: Optional[int] = None
    activ: bool = True


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
