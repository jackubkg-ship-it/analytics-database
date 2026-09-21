import socket
import time

from fastapi import Cookie, Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from .database import Base, engine, get_db, SessionLocal
from . import models, models_maintenance, auth
from .routers import upload, dashboard, equipment, auth_router, admin, maintenance

Base.metadata.create_all(bind=engine)


def _get_lan_ip() -> str:
    """IP компьютера в локальной сети - чтобы с телефона можно было зайти на http://<ip>:8000."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


LAN_IP = _get_lan_ip()


def _bootstrap_default_admin():
    """При самом первом запуске (пустая таблица пользователей) создаёт админа по умолчанию."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            salt, digest = auth.hash_password("admin")
            db.add(models.User(
                username="admin",
                password_salt=salt,
                password_hash=digest,
                role=auth.ROLE_ADMIN,
            ))
            db.commit()
            print("=" * 60)
            print("Standart admin hesabı yaradıldı:")
            print("  İstifadəçi adı: admin")
            print("  Şifrə: admin")
            print("Zəhmət olmasa daxil olduqdan sonra şifrəni dəyişin!")
            print("=" * 60)
    finally:
        db.close()


_bootstrap_default_admin()

print("=" * 60)
print(f"Mobil versiya üçün telefonda bu ünvanı açın: http://{LAN_IP}:8000/mobile")
print("(telefon və kompüter eyni Wi-Fi şəbəkəsində olmalıdır)")
print("=" * 60)

app = FastAPI(title="Контрактор Аналитика")

app.include_router(auth_router.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(dashboard.router)
app.include_router(equipment.router)
app.include_router(maintenance.router)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Меняется при каждом запуске сервера - добавляется в URL static-файлов (?v=...),
# чтобы браузер не подсовывал закэшированную старую версию CSS/JS после обновления кода.
ASSET_VERSION = str(int(time.time()))


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = auth.get_user_from_token(db, session_token)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "asset_version": ASSET_VERSION,
            "username": user.username,
            "role": user.role,
            "role_label": auth.ROLE_LABELS.get(user.role, user.role),
        },
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    # уже вошли - сразу на главную, повторный логин не нужен
    if auth.get_user_from_token(db, session_token):
        return RedirectResponse("/")
    return templates.TemplateResponse(
        request=request, name="login.html", context={"asset_version": ASSET_VERSION, "lan_ip": LAN_IP}
    )


@app.get("/maintenance", response_class=HTMLResponse)
def maintenance_page(
    request: Request,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = auth.get_user_from_token(db, session_token)
    if not user:
        return RedirectResponse("/login")
    if user.role != auth.ROLE_ADMIN:
        return RedirectResponse("/")
    return templates.TemplateResponse(
        request=request,
        name="maintenance.html",
        context={"asset_version": ASSET_VERSION, "username": user.username, "role": user.role},
    )


@app.get("/mobile", response_class=HTMLResponse)
def mobile_page(
    request: Request,
    session_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    user = auth.get_user_from_token(db, session_token)
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        request=request,
        name="mobile.html",
        context={
            "asset_version": ASSET_VERSION,
            "username": user.username,
            "role": user.role,
            "role_label": auth.ROLE_LABELS.get(user.role, user.role),
        },
    )
