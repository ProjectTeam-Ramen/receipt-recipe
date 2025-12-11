from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.backend.database import get_db
from app.backend.models import User

from .auth_routes import _hash_password, _verify_password, get_current_user

router = APIRouter()


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    username: str
    email: str
    birthday: Optional[date] = None
    created_at: datetime


@router.get("/me", response_model=UserResponse)
def read_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/me/password")
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stored_hash = getattr(current_user, "password_hash", None)
    if not isinstance(stored_hash, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No password set for user"
        )
    if not _verify_password(req.old_password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Old password incorrect"
        )

    setattr(current_user, "password_hash", _hash_password(req.new_password))
    db.add(current_user)
    db.commit()
    return {"message": "Password updated"}
