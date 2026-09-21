from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from .. import models, auth
from ..parser import extract_type_family

router = APIRouter(prefix="/api", tags=["dashboard"])

MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
    7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
}


@router.get("/periods")
def list_periods(db: Session = Depends(get_db), _user: models.User = Depends(auth.get_current_user)):
    rows = (
        db.query(models.UploadSheet.period_year, models.UploadSheet.period_month)
        .distinct()
        .order_by(models.UploadSheet.period_year.desc(), models.UploadSheet.period_month.desc())
        .all()
    )
    return [
        {"value": f"{y}-{m:02d}", "label": f"{MONTH_NAMES_RU.get(m, m)} {y}"}
        for y, m in rows
    ]


def _apply_period_filter(query, period: str | None):
    if period and period != "all":
        year, month = map(int, period.split("-"))
        query = query.filter(
            models.RepairRecord.period_year == year,
            models.RepairRecord.period_month == month,
        )
    return query


MONTH_ABBR_RU = {
    1: "Yan", 2: "Fev", 3: "Mar", 4: "Apr", 5: "May", 6: "İyn",
    7: "İyl", 8: "Avq", 9: "Sen", 10: "Okt", 11: "Noy", 12: "Dek",
}


@router.get("/years")
def list_years(db: Session = Depends(get_db), _user: models.User = Depends(auth.get_current_user)):
    rows = (
        db.query(models.UploadSheet.period_year)
        .distinct()
        .order_by(models.UploadSheet.period_year.desc())
        .all()
    )
    return [y for (y,) in rows]


@router.get("/yearly-summary")
def yearly_summary(year: int | None = Query(default=None), db: Session = Depends(get_db), _user: models.User = Depends(auth.get_current_user)):
    if year is None:
        latest = (
            db.query(models.UploadSheet.period_year)
            .order_by(models.UploadSheet.period_year.desc())
            .first()
        )
        year = latest[0] if latest else None

    contractors = db.query(models.Contractor).order_by(models.Contractor.id).all()
    result = []
    for contractor in contractors:
        monthly = [0.0] * 12
        equipment_monthly = [0] * 12
        equipment_total = 0
        if year is not None:
            rows = (
                db.query(models.RepairRecord.period_month, func.sum(models.RepairRecord.total_price))
                .filter(
                    models.RepairRecord.contractor_id == contractor.id,
                    models.RepairRecord.period_year == year,
                )
                .group_by(models.RepairRecord.period_month)
                .all()
            )
            for month, total in rows:
                monthly[month - 1] = round(total or 0, 2)

            equip_rows = (
                db.query(
                    models.RepairRecord.period_month,
                    func.count(func.distinct(models.RepairRecord.equipment_id)),
                )
                .filter(
                    models.RepairRecord.contractor_id == contractor.id,
                    models.RepairRecord.period_year == year,
                )
                .group_by(models.RepairRecord.period_month)
                .all()
            )
            for month, cnt in equip_rows:
                equipment_monthly[month - 1] = cnt

            equipment_total = (
                db.query(func.count(func.distinct(models.RepairRecord.equipment_id)))
                .filter(
                    models.RepairRecord.contractor_id == contractor.id,
                    models.RepairRecord.period_year == year,
                )
                .scalar()
            ) or 0

        result.append({
            "contractor": contractor.name,
            "monthly": monthly,
            "total": round(sum(monthly), 2),
            "equipment_monthly": equipment_monthly,
            "equipment_total": equipment_total,
        })

    return {
        "year": year,
        "months": [MONTH_ABBR_RU[m] for m in range(1, 13)],
        "contractors": result,
    }


@router.get("/brand-summary")
def brand_summary(year: int | None = Query(default=None), db: Session = Depends(get_db), _user: models.User = Depends(auth.get_current_user)):
    """Сводка по маркам/семействам техники (Kamaz, Niva, Xcmg и т.д.) - по всем подрядчикам вместе.
    Показываем все марки без группировки в 'остальное', чтобы не скрывать, что туда входит."""
    if year is None:
        latest = (
            db.query(models.UploadSheet.period_year)
            .order_by(models.UploadSheet.period_year.desc())
            .first()
        )
        year = latest[0] if latest else None

    brands: dict[str, dict] = {}
    if year is not None:
        rows = (
            db.query(
                models.RepairRecord.nv_type,
                models.RepairRecord.period_month,
                models.RepairRecord.total_price,
            )
            .filter(models.RepairRecord.period_year == year)
            .all()
        )
        for nv_type, month, total_price in rows:
            brand = extract_type_family(nv_type)
            b = brands.setdefault(brand, {"total": 0.0, "monthly": [0.0] * 12})
            b["total"] += total_price or 0
            b["monthly"][month - 1] += total_price or 0

    sorted_brands = sorted(brands.items(), key=lambda x: -x[1]["total"])
    result = [
        {"brand": name, "total": round(v["total"], 2), "monthly": [round(x, 2) for x in v["monthly"]]}
        for name, v in sorted_brands
    ]

    return {
        "year": year,
        "months": [MONTH_ABBR_RU[m] for m in range(1, 13)],
        "brands": result,
    }


@router.get("/dashboard")
def dashboard(period: str | None = Query(default=None), db: Session = Depends(get_db), _user: models.User = Depends(auth.get_current_user)):
    contractors = db.query(models.Contractor).order_by(models.Contractor.id).all()

    result = []
    for contractor in contractors:
        rows = (
            _apply_period_filter(
                db.query(
                    models.RepairRecord.nv_type,
                    models.RepairRecord.dq_number,
                    models.RepairRecord.total_price,
                    models.RepairRecord.description,
                    models.RepairRecord.work_date,
                ).filter(models.RepairRecord.contractor_id == contractor.id),
                period,
            )
            .all()
        )

        # группируем конкретные модели по общему названию (напр. 'Kamaz', 'Niva')
        families: dict[str, dict] = {}
        # частота ремонта по конкретному госномеру: сколько раз машина ЗАХОДИЛА в сервис
        # (уникальные даты) и сколько всего строк ремонта было сделано за эти заходы
        freq_by_dq: dict[str, dict] = {}
        # самые частые формулировки поломок/работ (по тексту 'İşin təsviri')
        issue_counts: dict[str, int] = {}

        for nv_type, dq_number, total_price, description, work_date in rows:
            family = extract_type_family(nv_type)
            fam = families.setdefault(family, {"total": 0.0, "equipment": {}})
            fam["total"] += total_price or 0
            eq = fam["equipment"].setdefault(dq_number, {"total": 0.0, "nv_type": nv_type})
            eq["total"] += total_price or 0
            eq["nv_type"] = nv_type  # оставляем последнее встреченное точное название модели

            freq = freq_by_dq.setdefault(dq_number, {"repair_count": 0, "visit_dates": set(), "nv_type": nv_type})
            freq["repair_count"] += 1
            if work_date:
                freq["visit_dates"].add(work_date)
            freq["nv_type"] = nv_type

            if description:
                key = description.strip()
                issue_counts[key] = issue_counts.get(key, 0) + 1

        by_type = []
        for family, data in sorted(families.items(), key=lambda x: -x[1]["total"]):
            equipment_list = sorted(
                (
                    {"dq_number": dq, "total": round(v["total"], 2), "nv_type": v["nv_type"]}
                    for dq, v in data["equipment"].items()
                ),
                key=lambda e: -e["total"],
            )
            by_type.append({
                "nv_type": family,
                "total": round(data["total"], 2),
                "equipment": equipment_list,
            })

        top_equipment_by_frequency = sorted(
            (
                {
                    "dq_number": dq,
                    "visit_count": len(v["visit_dates"]),
                    "repair_count": v["repair_count"],
                    "nv_type": v["nv_type"],
                }
                for dq, v in freq_by_dq.items()
            ),
            key=lambda x: (-x["visit_count"], -x["repair_count"]),
        )[:15]

        # мусорные/неинформативные формулировки не показываем в рейтинге поломок
        ISSUE_BLOCKLIST = {"0.2", "0.15", "servis haqqı", "səyyar xidmət", "səyyar xidməti"}
        top_issues = sorted(
            (
                {"description": desc, "count": c}
                for desc, c in issue_counts.items()
                if desc.strip().lower() not in ISSUE_BLOCKLIST
            ),
            key=lambda x: -x["count"],
        )[:8]

        contractor_total = round(sum(t["total"] for t in by_type), 2)
        equipment_count = len({dq for _, dq, _, _, _ in rows})
        result.append({
            "contractor_id": contractor.id,
            "contractor": contractor.name,
            "total": contractor_total,
            "equipment_count": equipment_count,
            "by_type": by_type,
            "top_equipment_by_frequency": top_equipment_by_frequency,
            "top_issues": top_issues,
        })

    return result
