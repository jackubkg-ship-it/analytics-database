import os
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from .. import models, auth
from ..parser import parse_workbook

router = APIRouter(prefix="/api", tags=["upload"])


def _get_or_create_contractor(db: Session, name: str) -> models.Contractor:
    contractor = db.query(models.Contractor).filter(models.Contractor.name == name).first()
    if not contractor:
        contractor = models.Contractor(name=name)
        db.add(contractor)
        db.flush()
    return contractor


def _get_or_create_equipment(db: Session, dq_number: str, nv_type: str, contractor_id: int) -> models.Equipment:
    equipment = db.query(models.Equipment).filter(models.Equipment.dq_number == dq_number).first()
    if not equipment:
        equipment = models.Equipment(dq_number=dq_number, nv_type=nv_type, contractor_id=contractor_id)
        db.add(equipment)
        db.flush()
    else:
        # техника могла обновить тип/подрядчика в новом файле - подхватываем актуальное значение
        if nv_type and equipment.nv_type != nv_type:
            equipment.nv_type = nv_type
        if equipment.contractor_id != contractor_id:
            equipment.contractor_id = contractor_id
    return equipment


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(auth.require_role(auth.ROLE_ADMIN)),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Ожидается файл .xlsx")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        parsed = parse_workbook(tmp_path, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    finally:
        os.unlink(tmp_path)

    upload = models.Upload(filename=file.filename)
    db.add(upload)
    db.flush()

    summary = []
    for sheet in parsed["sheets"]:
        contractor = _get_or_create_contractor(db, sheet["sheet_name"])

        if not sheet["rows"]:
            summary.append({"contractor": contractor.name, "rows_imported": 0, "total": 0, "note": "лист пуст"})
            continue

        existing_sheet = (
            db.query(models.UploadSheet)
            .filter(
                models.UploadSheet.contractor_id == contractor.id,
                models.UploadSheet.period_year == parsed["year"],
                models.UploadSheet.period_month == parsed["month"],
            )
            .first()
        )
        if existing_sheet:
            # переопределяем данные за этот период этим же подрядчиком (например, файл поправили и перезалили)
            db.query(models.RepairRecord).filter(
                models.RepairRecord.upload_sheet_id == existing_sheet.id
            ).delete()
            existing_sheet.upload_id = upload.id
            upload_sheet = existing_sheet
        else:
            upload_sheet = models.UploadSheet(
                upload_id=upload.id,
                contractor_id=contractor.id,
                sheet_name=sheet["sheet_name"],
                period_year=parsed["year"],
                period_month=parsed["month"],
            )
            db.add(upload_sheet)
            db.flush()

        total = 0.0
        for row in sheet["rows"]:
            equipment = _get_or_create_equipment(db, row["dq_number"], row["nv_type"], contractor.id)
            record = models.RepairRecord(
                upload_sheet_id=upload_sheet.id,
                contractor_id=contractor.id,
                equipment_id=equipment.id,
                period_year=parsed["year"],
                period_month=parsed["month"],
                **{k: v for k, v in row.items()},
            )
            db.add(record)
            total += row["total_price"] or 0

        upload_sheet.rows_imported = len(sheet["rows"])
        summary.append({
            "contractor": contractor.name,
            "rows_imported": len(sheet["rows"]),
            "total": round(total, 2),
        })

    db.commit()

    return {
        "filename": file.filename,
        "period": f"{parsed['year']}-{parsed['month']:02d}",
        "sheets": summary,
    }
