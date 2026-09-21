"""
Расчёт статуса ТО: для каждой пары (машина, вид ТО) берём применимое правило
(машина -> перекрывает марку), последнее выполнение и текущую наработку,
и вычисляем, что наступает раньше - срок по времени или по наработке.
"""
from datetime import date, timedelta
from sqlalchemy.orm import Session

from . import models_maintenance as mm

WARNING_DAYS = 14
WARNING_USAGE = 1000

STATUS_OVERDUE = "overdue"
STATUS_SOON = "soon"
STATUS_OK = "ok"
STATUS_UNKNOWN = "unknown"

_SEVERITY = {STATUS_UNKNOWN: 0, STATUS_OK: 1, STATUS_SOON: 2, STATUS_OVERDUE: 3}


def _worse(a: str, b: str) -> str:
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


def get_applicable_rule(db: Session, dq_number: str, brand: str, maintenance_type_id: int):
    """Правило для конкретной машины имеет приоритет над правилом марки."""
    rule = (
        db.query(mm.MaintenanceRule)
        .filter(
            mm.MaintenanceRule.scope == "equipment",
            mm.MaintenanceRule.scope_value == dq_number,
            mm.MaintenanceRule.maintenance_type_id == maintenance_type_id,
        )
        .first()
    )
    if rule:
        return rule
    return (
        db.query(mm.MaintenanceRule)
        .filter(
            mm.MaintenanceRule.scope == "brand",
            mm.MaintenanceRule.scope_value == brand,
            mm.MaintenanceRule.maintenance_type_id == maintenance_type_id,
        )
        .first()
    )


def _time_status(last_event, interval_days, today):
    if not interval_days or not last_event:
        return STATUS_UNKNOWN, None
    due_date = last_event.performed_date + timedelta(days=interval_days)
    days_left = (due_date - today).days
    if days_left < 0:
        return STATUS_OVERDUE, due_date
    if days_left <= WARNING_DAYS:
        return STATUS_SOON, due_date
    return STATUS_OK, due_date


def _usage_status(db: Session, dq_number, last_event, interval_usage, usage_unit):
    if not interval_usage or not usage_unit or not last_event:
        return STATUS_UNKNOWN, None, None

    performed_value = last_event.performed_km if usage_unit == "km" else last_event.performed_hours
    if performed_value is None:
        return STATUS_UNKNOWN, None, None

    current = (
        db.query(mm.CurrentUsage)
        .filter(mm.CurrentUsage.dq_number == dq_number, mm.CurrentUsage.unit == usage_unit)
        .first()
    )
    if not current:
        return STATUS_UNKNOWN, None, None

    due_value = performed_value + interval_usage
    remaining = due_value - current.value
    if remaining < 0:
        return STATUS_OVERDUE, due_value, current.value
    if remaining <= WARNING_USAGE:
        return STATUS_SOON, due_value, current.value
    return STATUS_OK, due_value, current.value


def compute_status_board(db: Session):
    """Возвращает список: одна строка на каждую применимую пару (машина, вид ТО)."""
    today = date.today()
    equipment_list = db.query(mm.TrackedEquipment).order_by(mm.TrackedEquipment.dq_number).all()
    types = db.query(mm.MaintenanceType).order_by(mm.MaintenanceType.id).all()

    board = []
    for eq in equipment_list:
        for mtype in types:
            rule = get_applicable_rule(db, eq.dq_number, eq.brand, mtype.id)
            if not rule:
                continue  # для этой машины/марки этот вид ТО не настроен - не показываем строку

            last_event = (
                db.query(mm.MaintenanceEvent)
                .filter(
                    mm.MaintenanceEvent.dq_number == eq.dq_number,
                    mm.MaintenanceEvent.maintenance_type_id == mtype.id,
                )
                .order_by(mm.MaintenanceEvent.performed_date.desc())
                .first()
            )

            time_status, due_date = _time_status(last_event, rule.interval_days, today)
            usage_status, due_usage, current_usage = _usage_status(
                db, eq.dq_number, last_event, rule.interval_usage, rule.usage_unit
            )

            overall = _worse(time_status, usage_status)

            board.append({
                "dq_number": eq.dq_number,
                "brand": eq.brand,
                "maintenance_type": mtype.name,
                "status": overall,
                "last_performed_date": last_event.performed_date.isoformat() if last_event else None,
                "due_date": due_date.isoformat() if due_date else None,
                "usage_unit": rule.usage_unit,
                "due_usage": due_usage,
                "current_usage": current_usage,
                "rule_scope": rule.scope,  # чтобы в интерфейсе показать, откуда взялось правило
            })

    # сначала самые срочные
    board.sort(key=lambda r: -_SEVERITY[r["status"]])
    return board
