from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, auth
from .. import models_maintenance as mm
from ..maintenance_logic import compute_status_board

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])

# Пока весь модуль - только для admin. Расширим на другие роли, когда решим по правам.
require_admin = auth.require_role(auth.ROLE_ADMIN)


# ---------- Виды ТО ----------

class MaintenanceTypeIn(BaseModel):
    name: str = Field(min_length=2, max_length=255)


@router.get("/types")
def list_types(db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    types = db.query(mm.MaintenanceType).order_by(mm.MaintenanceType.name).all()
    return [{"id": t.id, "name": t.name} for t in types]


@router.post("/types")
def create_type(payload: MaintenanceTypeIn, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    if db.query(mm.MaintenanceType).filter(mm.MaintenanceType.name == payload.name).first():
        raise HTTPException(400, "Bu ad artıq mövcuddur")
    t = mm.MaintenanceType(name=payload.name)
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"id": t.id, "name": t.name}


@router.delete("/types/{type_id}")
def delete_type(type_id: int, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    t = db.query(mm.MaintenanceType).filter(mm.MaintenanceType.id == type_id).first()
    if not t:
        raise HTTPException(404, "Tapılmadı")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---------- Реестр техники ----------

class TrackedEquipmentIn(BaseModel):
    dq_number: str = Field(min_length=1, max_length=100)
    brand: str = Field(min_length=1, max_length=255)


@router.get("/equipment")
def list_tracked_equipment(db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    rows = db.query(mm.TrackedEquipment).order_by(mm.TrackedEquipment.dq_number).all()
    return [{"id": r.id, "dq_number": r.dq_number, "brand": r.brand} for r in rows]


@router.post("/equipment")
def create_tracked_equipment(
    payload: TrackedEquipmentIn, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)
):
    from ..parser import normalize_dq_number
    dq = normalize_dq_number(payload.dq_number)
    if db.query(mm.TrackedEquipment).filter(mm.TrackedEquipment.dq_number == dq).first():
        raise HTTPException(400, "Bu texnika artıq reyestrdədir")
    row = mm.TrackedEquipment(dq_number=dq, brand=payload.brand.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "dq_number": row.dq_number, "brand": row.brand}


@router.delete("/equipment/{row_id}")
def delete_tracked_equipment(row_id: int, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    row = db.query(mm.TrackedEquipment).filter(mm.TrackedEquipment.id == row_id).first()
    if not row:
        raise HTTPException(404, "Tapılmadı")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------- Регламент (правила) ----------

class MaintenanceRuleIn(BaseModel):
    scope: str  # 'brand' | 'equipment'
    scope_value: str = Field(min_length=1, max_length=255)
    maintenance_type_id: int
    interval_days: int | None = None
    interval_usage: float | None = None
    usage_unit: str | None = None  # 'km' | 'hours'


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    rules = db.query(mm.MaintenanceRule).order_by(mm.MaintenanceRule.id).all()
    return [
        {
            "id": r.id,
            "scope": r.scope,
            "scope_value": r.scope_value,
            "maintenance_type_id": r.maintenance_type_id,
            "maintenance_type": r.maintenance_type.name,
            "interval_days": r.interval_days,
            "interval_usage": r.interval_usage,
            "usage_unit": r.usage_unit,
        }
        for r in rules
    ]


@router.post("/rules")
def create_rule(payload: MaintenanceRuleIn, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    if payload.scope not in ("brand", "equipment"):
        raise HTTPException(400, "scope 'brand' və ya 'equipment' olmalıdır")
    if not payload.interval_days and not payload.interval_usage:
        raise HTTPException(400, "Ən azı bir interval (vaxt və ya naработка) daxil edin")
    if payload.interval_usage and payload.usage_unit not in ("km", "hours"):
        raise HTTPException(400, "Naработка intervalı üçün ölçü vahidi (km/hours) tələb olunur")

    existing = (
        db.query(mm.MaintenanceRule)
        .filter(
            mm.MaintenanceRule.scope == payload.scope,
            mm.MaintenanceRule.scope_value == payload.scope_value,
            mm.MaintenanceRule.maintenance_type_id == payload.maintenance_type_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "Bu kombinasiya üçün qayda artıq mövcuddur")

    rule = mm.MaintenanceRule(**payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {"id": rule.id}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    rule = db.query(mm.MaintenanceRule).filter(mm.MaintenanceRule.id == rule_id).first()
    if not rule:
        raise HTTPException(404, "Tapılmadı")
    db.delete(rule)
    db.commit()
    return {"ok": True}


# ---------- Наработка ----------

class UsageReadingIn(BaseModel):
    dq_number: str
    unit: str  # 'km' | 'hours'
    value: float
    reading_date: date


def _record_usage(db: Session, dq_number: str, unit: str, value: float, reading_date: date, source: str,
                   user_id: int | None, provider: str | None = None):
    from ..parser import normalize_dq_number
    dq = normalize_dq_number(dq_number)

    db.add(mm.UsageReading(
        dq_number=dq, unit=unit, value=value, reading_date=reading_date,
        source=source, provider=provider, created_by_user_id=user_id,
    ))

    current = (
        db.query(mm.CurrentUsage)
        .filter(mm.CurrentUsage.dq_number == dq, mm.CurrentUsage.unit == unit)
        .first()
    )
    # обновляем "текущее" только если новое показание не старше уже известного
    if not current:
        db.add(mm.CurrentUsage(dq_number=dq, unit=unit, value=value, reading_date=reading_date, source=source, provider=provider))
    elif reading_date >= current.reading_date:
        current.value = value
        current.reading_date = reading_date
        current.source = source
        current.provider = provider


@router.post("/usage-readings")
def add_usage_reading(
    payload: UsageReadingIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    if payload.unit not in ("km", "hours"):
        raise HTTPException(400, "unit 'km' və ya 'hours' olmalıdır")
    _record_usage(db, payload.dq_number, payload.unit, payload.value, payload.reading_date, "manual", user.id)
    db.commit()
    return {"ok": True}


@router.get("/usage-readings")
def list_usage_readings(
    dq_number: str, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)
):
    from ..parser import normalize_dq_number
    dq = normalize_dq_number(dq_number)
    rows = (
        db.query(mm.UsageReading)
        .filter(mm.UsageReading.dq_number == dq)
        .order_by(mm.UsageReading.reading_date.desc())
        .all()
    )
    return [
        {"date": r.reading_date.isoformat(), "unit": r.unit, "value": r.value, "source": r.source}
        for r in rows
    ]


# ---------- События ТО ----------

class MaintenanceEventIn(BaseModel):
    dq_number: str
    maintenance_type_id: int
    performed_date: date
    performed_km: float | None = None
    performed_hours: float | None = None
    note: str | None = None


@router.post("/events")
def create_event(
    payload: MaintenanceEventIn, db: Session = Depends(get_db), user: models.User = Depends(require_admin)
):
    from ..parser import normalize_dq_number
    dq = normalize_dq_number(payload.dq_number)

    event = mm.MaintenanceEvent(
        dq_number=dq,
        maintenance_type_id=payload.maintenance_type_id,
        performed_date=payload.performed_date,
        performed_km=payload.performed_km,
        performed_hours=payload.performed_hours,
        note=payload.note,
        created_by_user_id=user.id,
    )
    db.add(event)

    # если наработка указана прямо здесь - это тоже валидное показание наработки
    if payload.performed_km is not None:
        _record_usage(db, dq, "km", payload.performed_km, payload.performed_date, "maintenance_event", user.id)
    if payload.performed_hours is not None:
        _record_usage(db, dq, "hours", payload.performed_hours, payload.performed_date, "maintenance_event", user.id)

    db.commit()
    return {"ok": True}


@router.get("/events")
def list_events(dq_number: str, db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    from ..parser import normalize_dq_number
    dq = normalize_dq_number(dq_number)
    rows = (
        db.query(mm.MaintenanceEvent)
        .filter(mm.MaintenanceEvent.dq_number == dq)
        .order_by(mm.MaintenanceEvent.performed_date.desc())
        .all()
    )
    return [
        {
            "date": r.performed_date.isoformat(),
            "maintenance_type": r.maintenance_type.name,
            "performed_km": r.performed_km,
            "performed_hours": r.performed_hours,
            "note": r.note,
        }
        for r in rows
    ]


# ---------- Доска статусов ----------

@router.get("/status")
def status_board(db: Session = Depends(get_db), _u: models.User = Depends(require_admin)):
    return compute_status_board(db)
