"""
Модуль регламента ТО. Спроектирован автономно - связь с основным Equipment/RepairRecord
идёт через dq_number как обычную строку (без FK), чтобы модуль можно было развивать
независимо и подключить к основной базе отдельным шагом позже.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, UniqueConstraint, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Base


class MaintenanceType(Base):
    """Вид планового обслуживания, например 'Motor yağı dəyişimi'."""
    __tablename__ = "maintenance_types"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TrackedEquipment(Base):
    """Локальный реестр техники, которую отслеживает модуль ТО (пока вводится вручную,
    позже синхронизируется с основной таблицей Equipment по dq_number)."""
    __tablename__ = "maintenance_tracked_equipment"

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), unique=True, nullable=False, index=True)
    brand = Column(String(255), nullable=False)  # марка/семейство, напр. 'Kamaz'
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MaintenanceRule(Base):
    """Регламент: интервал по времени и/или по наработке для вида ТО.
    scope='brand' -> действует на все машины этой марки (scope_value = 'Kamaz').
    scope='equipment' -> действует на одну конкретную машину (scope_value = DQ №-si)
    и имеет приоритет над правилом марки для того же вида ТО."""
    __tablename__ = "maintenance_rules"
    __table_args__ = (
        UniqueConstraint("scope", "scope_value", "maintenance_type_id", name="uq_rule_scope_type"),
    )

    id = Column(Integer, primary_key=True)
    scope = Column(String(20), nullable=False)  # 'brand' | 'equipment'
    scope_value = Column(String(255), nullable=False)
    maintenance_type_id = Column(Integer, ForeignKey("maintenance_types.id"), nullable=False)

    interval_days = Column(Integer, nullable=True)
    interval_usage = Column(Float, nullable=True)
    usage_unit = Column(String(10), nullable=True)  # 'km' | 'hours'

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    maintenance_type = relationship("MaintenanceType")


class CurrentUsage(Base):
    """Последнее известное показание наработки по машине - именно отсюда расчёт статуса
    берёт 'текущую' наработку. Журнал (UsageReading) хранит историю отдельно."""
    __tablename__ = "maintenance_current_usage"
    __table_args__ = (
        UniqueConstraint("dq_number", "unit", name="uq_current_usage_dq_unit"),
    )

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), nullable=False, index=True)
    unit = Column(String(10), nullable=False)  # 'km' | 'hours'
    value = Column(Float, nullable=False)
    reading_date = Column(Date, nullable=False)
    source = Column(String(20), nullable=False)  # 'manual' | 'maintenance_event' | 'gps_tracker'
    provider = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UsageReading(Base):
    """Полная история показаний наработки - для журнала/графика, расчёт статуса её не читает
    напрямую (смотрит CurrentUsage), но история остаётся для аудита."""
    __tablename__ = "maintenance_usage_readings"

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), nullable=False, index=True)
    unit = Column(String(10), nullable=False)
    value = Column(Float, nullable=False)
    reading_date = Column(Date, nullable=False)
    source = Column(String(20), nullable=False)
    provider = Column(String(100), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class MaintenanceEvent(Base):
    """Факт выполнения ТО - точка отсчёта для расчёта следующего срока."""
    __tablename__ = "maintenance_events"

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), nullable=False, index=True)
    maintenance_type_id = Column(Integer, ForeignKey("maintenance_types.id"), nullable=False)
    performed_date = Column(Date, nullable=False)
    performed_km = Column(Float, nullable=True)
    performed_hours = Column(Float, nullable=True)
    note = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    maintenance_type = relationship("MaintenanceType")


class TrackerDevice(Base):
    """Заготовка под GPS-трекер - пока не используется. Когда появится провайдер,
    сюда впишется связь машина -> устройство, и импорт будет писать показания
    через ту же точку входа (CurrentUsage/UsageReading, source='gps_tracker')."""
    __tablename__ = "maintenance_tracker_devices"

    id = Column(Integer, primary_key=True)
    dq_number = Column(String(100), nullable=False, index=True)
    provider = Column(String(100), nullable=False)
    external_device_id = Column(String(255), nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
