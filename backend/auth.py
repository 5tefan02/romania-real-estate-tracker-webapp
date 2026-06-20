# autentificare - verific parola, fac JWT, dependinta pt rutele protejate

import os
from datetime import datetime, timedelta, timezone

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from db.connection import get_db
from db.models import AppUser

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

COOKIE_NAME = "access_token"

# parolele sunt hash-uite cu bcrypt
def verify_password(plain_password: str, hashed_password: str) -> bool:
    parola_bytes = plain_password.encode("utf-8")
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(parola_bytes, hash_bytes)


def hash_password(plain_password: str) -> str:
    # folosit la inregistrare ca sa nu salvez parola in clar
    parola_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(parola_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)) -> AppUser:

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise JWTError("missing sub")
        user_id = int(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
        )

    # daca admin a dezactivat userul in timp ce el era logat, il dau afara
    # la urmatorul request (token-ul mai e valid dar contul nu mai e activ)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Contul tau a fost dezactivat.",
        )

    return user


def require_admin(current_user: AppUser = Depends(get_current_user)) -> AppUser:
    # dependency pt rutele care cer rol admin
    # se foloseste asa: current_user: AppUser = Depends(require_admin)
    # daca userul nu e admin -> 403 si requestul nu mai ajunge la handler
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
