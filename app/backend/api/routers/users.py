
from typing import Dict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# reuse auth module's user store and helpers
from .auth_routes import get_current_user, _verify_password, _hash_password, _USERS

router = APIRouter()


@router.get("/me")
def read_me(current_user: Dict = Depends(get_current_user)):
    # return public view
    return {"user_id": current_user["user_id"], "username": current_user["username"], "email": current_user["email"]}


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


@router.put("/me/password")
def change_password(req: PasswordChangeRequest, current_user: Dict = Depends(get_current_user)):
    email = current_user["email"]
    stored = current_user.get("password_hash")
    if not stored:
        raise HTTPException(status_code=400, detail="No password set for user")
    if not _verify_password(req.old_password, stored):
        raise HTTPException(status_code=400, detail="Old password incorrect")
    _USERS[email]["password_hash"] = _hash_password(req.new_password)
    return {"message": "Password updated"}
