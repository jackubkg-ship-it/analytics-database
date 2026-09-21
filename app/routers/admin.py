from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/api/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=4, max_length=200)
    role: str


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_role(auth.ROLE_ADMIN)),
):
    users = db.query(models.User).order_by(models.User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "role_label": auth.ROLE_LABELS.get(u.role, u.role),
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_role(auth.ROLE_ADMIN)),
):
    if payload.role not in auth.ALL_ROLES:
        raise HTTPException(400, "Yanlış rol")

    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(400, "Bu istifadəçi adı artıq mövcuddur")

    salt, digest = auth.hash_password(payload.password)
    user = models.User(username=payload.username, password_salt=salt, password_hash=digest, role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(auth.require_role(auth.ROLE_ADMIN)),
):
    if user_id == admin.id:
        raise HTTPException(400, "Öz hesabınızı silə bilməzsiniz")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(404, "İstifadəçi tapılmadı")

    if user.role == auth.ROLE_ADMIN:
        admin_count = db.query(models.User).filter(models.User.role == auth.ROLE_ADMIN).count()
        if admin_count <= 1:
            raise HTTPException(400, "Sistemdə ən azı bir admin qalmalıdır")

    db.delete(user)
    db.commit()
    return {"ok": True}
