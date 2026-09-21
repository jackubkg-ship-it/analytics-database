from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    """Пользователь системы: admin (полный доступ), viewer_full (графики + история),
    viewer_charts (только графики, без истории ремонта и без загрузки файлов)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    password_salt = Column(String(64), nullable=False)
    role = Column(String(20), nullable=False)  # 'admin' | 'viewer_full' | 'viewer_charts'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Токен сессии после входа - хранится в базе, чтобы вход не слетал при перезапуске сервера."""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="sessions")


class Contractor(Base):
    """Один подрядчик = один лист (вкладка) в загружаемом Excel-файле."""
    __tablename__ = "contractors"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)  # название листа

    equipment = relationship("Equipment", back_populates="contractor")
    records = relationship("RepairRecord", back_populates="contractor")


class Equipment(Base):
    """Единица техники. Уникальный ключ - номер из колонки 'DQ №-si'."""
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), unique=True, nullable=False, index=True)
    nv_type = Column(String(255), nullable=False)  # 'NV növü' - модель/тип техники
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)

    contractor = relationship("Contractor", back_populates="equipment")
    records = relationship("RepairRecord", back_populates="equipment")


class Upload(Base):
    """Один загруженный файл (например August_2026.xlsx)."""
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True)
    filename = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    sheets = relationship("UploadSheet", back_populates="upload")


class UploadSheet(Base):
    """Один лист внутри загруженного файла = данные одного подрядчика за один период."""
    __tablename__ = "upload_sheets"
    __table_args__ = (
        UniqueConstraint("contractor_id", "period_year", "period_month", name="uq_contractor_period"),
    )

    id = Column(Integer, primary_key=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    sheet_name = Column(String(255), nullable=False)
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)  # 1-12
    rows_imported = Column(Integer, default=0)

    upload = relationship("Upload", back_populates="sheets")
    contractor = relationship("Contractor")
    records = relationship("RepairRecord", back_populates="upload_sheet", cascade="all, delete-orphan")


class RepairRecord(Base):
    """Одна строка таблицы ремонта - переносится в БД как есть, без потери данных."""
    __tablename__ = "repair_records"

    id = Column(Integer, primary_key=True)
    upload_sheet_id = Column(Integer, ForeignKey("upload_sheets.id"), nullable=False)
    contractor_id = Column(Integer, ForeignKey("contractors.id"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipment.id"), nullable=False)

    # денормализовано для быстрых выборок по периоду
    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)

    row_no = Column(Integer)                 # S/S
    work_date = Column(Date)                 # Tarix
    description = Column(Text)               # İşin təsviri
    qty = Column(Float)                      # Say
    unit = Column(String(50))                # Ölçü vahidi
    price = Column(Float)                     # Qiymət
    total_price = Column(Float)              # Yekun məbləğ
    schedule_no = Column(String(100))        # Cədvəl Sıra sayı
    customer = Column(String(255))           # Sifarişçi (A.S.A.)
    performer = Column(String(255))          # İş İcraçısı (A.S.A.)
    work_type = Column(String(255))          # İşin növü
    work_no = Column(String(100))            # İş №-si
    dq_number = Column(String(100))          # DQ №-si (дублируется для удобства выборок)
    nv_type = Column(String(255))            # NV növü (дублируется для удобства выборок)
    area = Column(String(255))               # Ərazi
    note = Column(Text)                      # Qeyd

    contractor = relationship("Contractor", back_populates="records")
    equipment = relationship("Equipment", back_populates="records")
    upload_sheet = relationship("UploadSheet", back_populates="records")
