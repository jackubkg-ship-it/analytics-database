from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, auth
from ..parser import normalize_dq_number, extract_type_family

router = APIRouter(prefix="/api", tags=["equipment"])


@router.get("/equipment/search")
def equipment_search(
    q: str = Query(default=""),
    contractor_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: models.User = Depends(auth.require_role(auth.ROLE_ADMIN, auth.ROLE_VIEWER_FULL)),
):
    """Поиск техники по (части) номера DQ №-si - устойчив к разным форматам записи.
    Пустой q -> возвращает весь список (используется кнопкой 'Təmir məlumatları').
    contractor_id -> ограничивает список техникой, которая реально обслуживалась
    именно у этого подрядчика (по факту наличия записей ремонта в базе)."""
    normalized_q = normalize_dq_number(q) if q else ""

    query = (
        db.query(models.Equipment)
        .filter(models.Equipment.dq_number.ilike(f"%{normalized_q}%"))
        .filter(models.Equipment.records.any())  # скрываем "осиротевшие" карточки без единого ремонта
    )
    if contractor_id is not None:
        query = query.filter(
            models.Equipment.records.any(models.RepairRecord.contractor_id == contractor_id)
        )

    matches = query.order_by(models.Equipment.dq_number).limit(500).all()

    results = []
    for eq in matches:
        contractors = (
            db.query(models.Contractor.name)
            .join(models.RepairRecord, models.RepairRecord.contractor_id == models.Contractor.id)
            .filter(models.RepairRecord.equipment_id == eq.id)
            .distinct()
            .all()
        )
        results.append({
            "dq_number": eq.dq_number,
            "nv_type": eq.nv_type,
            "brand": extract_type_family(eq.nv_type),
            "contractors": [c[0] for c in contractors],
        })
    return results


@router.get("/equipment/by-brand")
def equipment_by_brand(
    contractor_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: models.User = Depends(auth.require_role(auth.ROLE_ADMIN, auth.ROLE_VIEWER_FULL)),
):
    """Вся техника, сгруппированная по марке/семейству (Kamaz, Niva и т.д.) - для просмотра
    'Марка -> список машин этой марки' в окне 'Təmir məlumatları'."""
    query = db.query(models.Equipment).filter(models.Equipment.records.any())
    if contractor_id is not None:
        query = query.filter(
            models.Equipment.records.any(models.RepairRecord.contractor_id == contractor_id)
        )
    equipment_list = query.all()

    # подрядчиков по каждой единице техники подгружаем одним запросом (без N+1)
    contractor_rows = (
        db.query(models.RepairRecord.equipment_id, models.Contractor.name)
        .join(models.Contractor, models.RepairRecord.contractor_id == models.Contractor.id)
        .distinct()
        .all()
    )
    contractor_map: dict[int, set] = {}
    for eq_id, cname in contractor_rows:
        contractor_map.setdefault(eq_id, set()).add(cname)

    brands: dict[str, list] = {}
    for eq in equipment_list:
        brand = extract_type_family(eq.nv_type)
        brands.setdefault(brand, []).append({
            "dq_number": eq.dq_number,
            "nv_type": eq.nv_type,
            "contractors": sorted(contractor_map.get(eq.id, [])),
        })

    return [
        {"brand": name, "count": len(items), "equipment": sorted(items, key=lambda e: e["dq_number"])}
        for name, items in sorted(brands.items(), key=lambda x: -len(x[1]))
    ]


@router.get("/equipment/{dq_number}/history")
def equipment_history(
    dq_number: str,
    period: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: models.User = Depends(auth.require_role(auth.ROLE_ADMIN, auth.ROLE_VIEWER_FULL)),
):
    normalized = normalize_dq_number(dq_number)
    equipment = db.query(models.Equipment).filter(models.Equipment.dq_number == normalized).first()
    if not equipment:
        raise HTTPException(404, "Техника с таким DQ №-si не найдена")

    query = db.query(models.RepairRecord).filter(models.RepairRecord.equipment_id == equipment.id)
    if period and period != "all":
        year, month = map(int, period.split("-"))
        query = query.filter(
            models.RepairRecord.period_year == year,
            models.RepairRecord.period_month == month,
        )
    records = query.order_by(models.RepairRecord.work_date.asc().nullslast()).all()

    total = round(sum(r.total_price or 0 for r in records), 2)

    # разбивка одной и той же единицы техники по подрядчикам, которые с ней работали,
    # и по месяцам - на случай, если несколько подрядчиков обслуживали одну машину
    by_contractor: dict[str, float] = {}
    by_month: dict[str, float] = {}
    for r in records:
        cname = r.contractor.name
        by_contractor[cname] = by_contractor.get(cname, 0) + (r.total_price or 0)
        mkey = f"{r.period_year}-{r.period_month:02d}"
        by_month[mkey] = by_month.get(mkey, 0) + (r.total_price or 0)

    return {
        "dq_number": equipment.dq_number,
        "nv_type": equipment.nv_type,
        "total": total,
        "by_contractor": [
            {"contractor": k, "total": round(v, 2)}
            for k, v in sorted(by_contractor.items(), key=lambda x: -x[1])
        ],
        "by_month": [
            {"period": k, "total": round(v, 2)}
            for k, v in sorted(by_month.items())
        ],
        "records": [
            {
                "date": r.work_date.isoformat() if r.work_date else None,
                "description": r.description,
                "qty": r.qty,
                "unit": r.unit,
                "price": r.price,
                "total_price": r.total_price,
                "work_type": r.work_type,
                "performer": r.performer,
                "area": r.area,
                "note": r.note,
                "period": f"{r.period_year}-{r.period_month:02d}",
                "contractor": r.contractor.name,
            }
            for r in records
        ],
    }
