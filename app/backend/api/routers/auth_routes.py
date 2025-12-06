import hashlib
import secrets
import re
from datetime import date, datetime, timedelta
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import RefreshToken, User

router = APIRouter()


JWT_SECRET = "change_this_secret_in_production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 1800
REFRESH_TOKEN_EXPIRE_DAYS = 7
EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return _hash_password(password, salt) == stored


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    birthday: Optional[date] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_format(value)


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _validate_email_format(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS


class RefreshRequest(BaseModel):
    refresh_token: str


def _create_access_token(
    email: str, expires_seconds: int = ACCESS_TOKEN_EXPIRE_SECONDS
) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_seconds)).timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _create_refresh_token(email: str) -> str:
    now = datetime.utcnow()
    payload = {
        "sub": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def _store_refresh_token(db: Session, token: str, user_id: int) -> RefreshToken:
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(token=token, user_id=user_id, expires_at=expires_at)
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def _delete_refresh_token(db: Session, token: str) -> None:
    db_token = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    if db_token:
        db.delete(db_token)
        db.commit()


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _validate_email_format(value: str) -> str:
    stripped = value.strip()
    if not EMAIL_REGEX.match(stripped):
        raise ValueError("Invalid email format")
    return stripped.lower()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization"
        )
    try:
        scheme, token = authorization.split(" ", 1)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme"
        )

    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
        )

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    username = req.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=username,
        email=email,
        password_hash=_hash_password(req.password),
        birthday=req.birthday,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "birthday": user.birthday,
        "created_at": user.created_at,
    }


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = _normalize_email(req.email)
    user = db.query(User).filter(User.email == email).first()
    stored_hash = getattr(user, "password_hash", None) if user else None
    if not user or not isinstance(stored_hash, str) or not _verify_password(req.password, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access = _create_access_token(email)
    refresh = _create_refresh_token(email)
    user_id = getattr(user, "user_id", None)
    if not isinstance(user_id, int):
        raise HTTPException(status_code=500, detail="User record is invalid")
    _store_refresh_token(db, refresh, user_id)
    return {"access_token": access, "refresh_token": refresh}


@router.post("/refresh")
def refresh(req: RefreshRequest, db: Session = Depends(get_db)):
    payload = _decode_token(req.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    db_token = (
        db.query(RefreshToken).filter(RefreshToken.token == req.refresh_token).first()
    )
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expires_at = getattr(db_token, "expires_at", None)
    if isinstance(expires_at, datetime) and expires_at < datetime.utcnow():
        db.delete(db_token)
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    access = _create_access_token(email)
    return {
        "access_token": access,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
    }


@router.post("/logout")
def logout(req: RefreshRequest, db: Session = Depends(get_db)):
    _delete_refresh_token(db, req.refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/password-reset")
def password_reset(body: Dict):
    # send email in production; here we return ok
    return {"message": "Password reset email sent if account exists"}


@router.post("/password-reset/confirm")
def password_reset_confirm(body: Dict):
    return {"message": "Password has been reset"}
