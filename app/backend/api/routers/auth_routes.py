from typing import Dict

from fastapi import APIRouter, HTTPException, status
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# simple in-memory user store for demo purposes
_USERS: Dict[str, Dict] = {}
_NEXT_USER_ID = 1


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 1800


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest):
    global _NEXT_USER_ID
    if req.email in _USERS:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = {
        "user_id": _NEXT_USER_ID,
        "username": req.username,
        "email": req.email,
        "password_hash": pwd_context.hash(req.password),
    }
    _USERS[req.email] = user
    _NEXT_USER_ID += 1
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "email": user["email"],
    }


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest):
    user = _USERS.get(req.email)
    if not user or not pwd_context.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # For demo, tokens are simple strings; replace with real JWT in production
    return {
        "access_token": f"access-{user['user_id']}",
        "refresh_token": f"refresh-{user['user_id']}",
    }


@router.post("/refresh")
def refresh(token: dict):
    # stub implementation
    return {
        "access_token": "new-access-token",
        "token_type": "Bearer",
        "expires_in": 1800,
    }


@router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}


@router.post("/password-reset")
def password_reset(body: dict):
    # send email in production; here we return ok
    return {"message": "Password reset email sent if account exists"}


@router.post("/password-reset/confirm")
def password_reset_confirm(body: dict):
    return {"message": "Password has been reset"}
