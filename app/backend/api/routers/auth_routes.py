import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
import jwt

router = APIRouter()


# Config (for demo store the secret here; in production use env vars / vault)
JWT_SECRET = "change_this_secret_in_production"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 1800  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7


# simple hash helpers (lightweight demo)
def _hash_password(password: str, salt: str = None) -> str:
    if salt is None:
        salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"{salt}${h}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$", 1)
    except Exception:
        return False
    return _hash_password(password, salt) == stored


# simple in-memory user store for demo purposes keyed by email
_USERS: Dict[str, Dict] = {}
_NEXT_USER_ID = 1

# simple in-memory refresh token store: token -> email
_REFRESH_TOKENS: Dict[str, str] = {}


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_SECONDS


def _create_access_token(email: str, expires_seconds: int = ACCESS_TOKEN_EXPIRE_SECONDS) -> str:
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
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    _REFRESH_TOKENS[token] = email
    return token


def _decode_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization")
    try:
        scheme, token = authorization.split(" ", 1)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth scheme")
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    email = payload.get("sub")
    user = _USERS.get(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    global _NEXT_USER_ID
    if req.email in _USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "user_id": _NEXT_USER_ID,
        "username": req.username,
        "email": req.email,
        "password_hash": _hash_password(req.password),
    }
    _USERS[req.email] = user
    _NEXT_USER_ID += 1
    return {"user_id": user["user_id"], "username": user["username"], "email": user["email"]}


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = _USERS.get(req.email)
    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = _create_access_token(req.email)
    refresh = _create_refresh_token(req.email)
    return {"access_token": access, "refresh_token": refresh}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh")
def refresh(req: RefreshRequest):
    token = req.refresh_token
    # check stored
    if token not in _REFRESH_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    payload = _decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    email = payload.get("sub")
    # issue new access
    access = _create_access_token(email)
    return {"access_token": access, "token_type": "Bearer", "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS}


@router.post("/logout")
def logout(req: RefreshRequest):
    # remove refresh token to invalidate
    token = req.refresh_token
    _REFRESH_TOKENS.pop(token, None)
    return {"message": "Successfully logged out"}


@router.post("/password-reset")
def password_reset(body: Dict):
    # send email in production; here we return ok
    return {"message": "Password reset email sent if account exists"}


@router.post("/password-reset/confirm")
def password_reset_confirm(body: Dict):
    return {"message": "Password has been reset"}
