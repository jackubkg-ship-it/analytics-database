"""
Разбор загружаемого xlsx-файла.

Правила (заданы пользователем):
- каждый лист = один подрядчик, имя листа = имя подрядчика
- имя файла определяет период (месяц/год), например "August_2026.xlsx" -> август 2026
- заголовки колонок фиксированы, но могут отличаться переносами строк/пробелами
- строки без номера техники (DQ №-si) пропускаются - это пустые/служебные строки
"""
import re
from datetime import datetime, date
from dateutil import parser as dateparser

import openpyxl

# нормализованный заголовок -> имя поля в модели RepairRecord
HEADER_MAP = {
    "s/s": "row_no",
    "tarix": "work_date",
    "işin təsviri": "description",
    "say": "qty",
    "ölçü vahidi": "unit",
    "qiymət": "price",
    "yekun məbləğ": "total_price",
    "cədvəl sıra sayı": "schedule_no",
    "sifarişçi (a.s.a.)": "customer",
    "iş icraçısı (a.s.a.)": "performer",
    "işin növü": "work_type",
    "iş №-si": "work_no",
    "dq №-si": "dq_number",
    "nv növü": "nv_type",
    "ərazi": "area",
    "qeyd": "note",
}

MONTHS = {
    # English
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
    # Azerbaijani
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may_az": 5,
    "iyun": 6, "iyul": 7, "avqust": 8, "avgust": 8, "sentyabr": 9,
    "oktyabr": 10, "noyabr": 11, "dekabr": 12,
}


def extract_type_family(nv_type) -> str:
    """
    Группирует конкретные модели техники по общему названию (бренду/семейству),
    например 'KAMAZ 43118 Truck trailler' и 'Kamaz vaccum' -> 'Kamaz',
    'Niva-Lada-21214' и 'NIVA-VAZ-21214' -> 'Niva'.
    Берёт первое слово названия (до пробела или дефиса) и приводит к единому регистру.
    Эвристика не идеальна для нестандартных названий, но покрывает основные случаи.
    """
    if not nv_type:
        return "Naməlum"
    text = str(nv_type).strip()
    lowered = text.lower()
    match = re.match(r"[^\s\-]+", text)
    word = match.group(0) if match else text
    # для группировки марок важнее объединить 'NIVA' и 'NİVA' в одно имя, чем строго
    # следовать турецким правилам регистра (где обычная 'I' и 'İ' дают разные буквы)
    family = (word[0].upper() + word[1:].replace("İ", "i").replace("I", "i").lower()) if word else word

    # Niva Pikap - отдельная группа, чтобы не смешивать пикапы с обычной Нивой
    if family in ("Niva", "Vaz") and re.search(r"pikap|pickup", lowered):
        return "Niva Pikap"

    return family


def normalize_dq_number(value) -> str:
    """
    Приводит номер техники к единому виду, чтобы разные подрядчики,
    вписывающие один и тот же номер по-разному (с пробелами вокруг дефисов,
    в разном регистре и т.п.), считались одной и той же единицей техники.
    Пример: '77 - JF - 378' и '77-JF-378' -> '77-JF-378'.
    """
    text = str(value).strip().upper()
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_header(value) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    # азербайджанская İ/I ломает обычный .lower() (даёт "i" + комбинирующую точку) -
    # приводим явно, до стандартного lower()
    text = text.replace("İ", "i").replace("I", "ı")
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_period_from_filename(filename: str):
    """Возвращает (year, month) исходя из имени файла, например 'August_2026.xlsx' -> (2026, 8)."""
    name = re.sub(r"\.[^.]+$", "", filename)  # убрать расширение
    # азербайджанская İ/I ломает обычный .lower() - приводим явно, как и в заголовках
    name = name.replace("İ", "i").replace("I", "ı")
    lowered = name.lower().replace("_", " ").replace("-", " ")

    # числовые паттерны YYYY MM или MM YYYY
    m = re.search(r"(20\d{2})\D{0,3}(\d{1,2})\b", lowered)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return year, month
    m = re.search(r"\b(\d{1,2})\D{0,3}(20\d{2})", lowered)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if 1 <= month <= 12:
            return year, month

    # название месяца + год
    year_match = re.search(r"20\d{2}", lowered)
    year = int(year_match.group(0)) if year_match else None
    for token in re.split(r"\s+", lowered):
        token_clean = token.strip(",.;")
        if token_clean in MONTHS:
            month = MONTHS[token_clean]
            if year:
                return year, month
    if year:
        raise ValueError(
            f"В имени файла '{filename}' найден год {year}, но не удалось распознать месяц. "
            "Переименуйте файл, например 'August_2026.xlsx' или '2026-08.xlsx'."
        )
    raise ValueError(
        f"Не удалось определить месяц/год из имени файла '{filename}'. "
        "Ожидается формат вроде 'August_2026.xlsx', 'Avqust_2026.xlsx' или '2026-08.xlsx'."
    )


def _parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return dateparser.parse(str(value), dayfirst=True).date()
    except (ValueError, OverflowError):
        return None


def _to_float(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ".").strip())
    except ValueError:
        return None


def _is_default_sheet_name(name: str) -> bool:
    """Проверяет, похоже ли название вкладки на автоматическое имя Excel (Sheet1, Лист2, Vərəq1 и т.п.)."""
    return bool(re.match(r"^(sheet|лист|vərəq|varaq)\s*\d*$", name.strip(), flags=re.IGNORECASE))


def _find_header_row(ws, max_scan=10):
    for r in range(1, max_scan + 1):
        for c in range(1, ws.max_column + 1):
            if _normalize_header(ws.cell(row=r, column=c).value) == "s/s":
                return r
    return None


def parse_workbook(file_path: str, filename: str):
    """
    Возвращает список словарей:
    [{"sheet_name": ..., "rows": [ {row_no, work_date, ..., dq_number, nv_type}, ... ]}, ...]
    Пустые листы (без данных) возвращаются с rows=[].
    """
    year, month = parse_period_from_filename(filename)
    wb = openpyxl.load_workbook(file_path, data_only=True)

    result = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        header_row = _find_header_row(ws)
        rows = []
        if header_row:
            col_to_field = {}
            for c in range(1, ws.max_column + 1):
                field = HEADER_MAP.get(_normalize_header(ws.cell(row=header_row, column=c).value))
                if field:
                    col_to_field[c] = field

            for r in range(header_row + 1, ws.max_row + 1):
                raw = {}
                for c, field in col_to_field.items():
                    raw[field] = ws.cell(row=r, column=c).value

                dq_number = normalize_dq_number(raw.get("dq_number")) if raw.get("dq_number") not in (None, "") else None
                description = raw.get("description")
                qty_value = _to_float(raw.get("qty"))
                price_value = _to_float(raw.get("price"))
                total_value = _to_float(raw.get("total_price"))
                if total_value is None and qty_value is not None and price_value is not None:
                    # 'Yekun məbləğ' иногда хранится как формула (=Qiymət*Say) без сохранённого
                    # значения (файл пересохранён не в Excel) - тогда считаем сумму сами.
                    total_value = round(qty_value * price_value, 2)
                # пропускаем полностью пустые строки / строки без привязки к технике
                if not dq_number or (description in (None, "") and total_value in (None, "")):
                    continue

                rows.append({
                    "row_no": int(raw["row_no"]) if isinstance(raw.get("row_no"), (int, float)) else None,
                    "work_date": _parse_date(raw.get("work_date")),
                    "description": str(description).strip() if description else None,
                    "qty": qty_value,
                    "unit": str(raw.get("unit")).strip() if raw.get("unit") else None,
                    "price": price_value,
                    "total_price": total_value,
                    "schedule_no": str(raw.get("schedule_no")).strip() if raw.get("schedule_no") not in (None, "") else None,
                    "customer": str(raw.get("customer")).strip() if raw.get("customer") else None,
                    "performer": str(raw.get("performer")).strip() if raw.get("performer") else None,
                    "work_type": str(raw.get("work_type")).strip() if raw.get("work_type") else None,
                    "work_no": str(raw.get("work_no")).strip() if raw.get("work_no") not in (None, "") else None,
                    "dq_number": dq_number,
                    "nv_type": str(raw.get("nv_type")).strip() if raw.get("nv_type") else "Naməlum",
                    "area": str(raw.get("area")).strip() if raw.get("area") else None,
                    "note": str(raw.get("note")).strip() if raw.get("note") else None,
                })

        clean_name = sheet_name.strip()
        if rows and _is_default_sheet_name(clean_name):
            raise ValueError(
                f"Vərəq '{clean_name}' faylında '{filename}' hələ adlandırılmayıb (defolt Excel adı). "
                "Bu vərəqi podratçının adı ilə adlandırın (məs. 'Helius PRO GLTS') və faylı yenidən yükləyin - "
                "əks halda proqram bunu tamam ayrı, yanlış podratçı kimi qeyd edəcək."
            )

        result.append({"sheet_name": clean_name, "rows": rows})

    return {"year": year, "month": month, "sheets": result}
