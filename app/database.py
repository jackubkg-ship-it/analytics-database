import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# По умолчанию - локальный файл SQLite (ничего дополнительно устанавливать не нужно).
# Если задать переменную окружения DATABASE_URL (например на сервере, с PostgreSQL),
# приложение переключится на неё без изменений в коде.
DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "contractors.db")
os.makedirs(os.path.dirname(DEFAULT_SQLITE_PATH), exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
