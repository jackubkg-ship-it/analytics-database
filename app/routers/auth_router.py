from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not auth.verify_password(payload.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=401, detail="İstifadəçi adı və ya şifrə yanlışdır")

    token = auth.create_session(db, user)
    response.set_cookie(
        key=auth.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,  # 30 gün
    )
    return {"ok": True, "username": user.username, "role": user.role}


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if session_token:
        db.query(models.UserSession).filter(models.UserSession.token == session_token).delete()
        db.commit()
    response.delete_cookie(auth.SESSION_COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: models.User = Depends(auth.get_current_user)):
    return {
        "username": user.username,
        "role": user.role,
        "role_label": auth.ROLE_LABELS.get(user.role, user.role),
    }
