"""
Простая аутентификация на сессионных токенах - без внешних зависимостей
(hashlib/secrets из стандартной библиотеки достаточно для локального инструмента).
"""
import hashlib
import secrets

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SESSION_COOKIE_NAME = "session_token"

ROLE_ADMIN = "admin"
ROLE_VIEWER_FULL = "viewer_full"
ROLE_VIEWER_CHARTS = "viewer_charts"
ALL_ROLES = (ROLE_ADMIN, ROLE_VIEWER_FULL, ROLE_VIEWER_CHARTS)

ROLE_LABELS = {
    ROLE_ADMIN: "Admin",
    ROLE_VIEWER_FULL: "Qrafiklər + tarixçə",
    ROLE_VIEWER_CHARTS: "Yalnız qrafiklər",
}


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
    return salt, digest


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, digest = hash_password(password, salt)
    return secrets.compare_digest(digest, expected_hash)


def create_session(db: Session, user: models.User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(models.UserSession(token=token, user_id=user.id))
    db.commit()
    return token


def get_user_from_token(db: Session, token: str | None) -> models.User | None:
    if not token:
        return None
    session = db.query(models.UserSession).filter(models.UserSession.token == token).first()
    return session.user if session else None


def get_current_user(
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    user = get_user_from_token(db, session_token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Giriş tələb olunur")
    return user


def require_role(*roles: str):
    def checker(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu əməliyyat üçün icazəniz yoxdur",
            )
        return user
    return checker
