import re

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas

DTC_PATTERN = re.compile(r"\b[PBCU]\d{4}\b", re.IGNORECASE)
MILEAGE_PATTERN = re.compile(r"\b(\d{2,3})(?:[\s.]?bin)\b", re.IGNORECASE)


def build_search_text(payload: schemas.WorkOrderCreate) -> str:
    values = [
        payload.customer_complaint,
        payload.symptoms,
        payload.diagnosis,
        payload.actions,
        payload.result,
        payload.voice_transcript,
        " ".join(item.code for item in payload.dtc_codes),
    ]
    return " ".join(value.strip() for value in values if value and value.strip())


def extract_preview(text: str) -> schemas.ExtractionPreview:
    dtc_codes = sorted({match.upper() for match in DTC_PATTERN.findall(text)})
    mileage_match = MILEAGE_PATTERN.search(text)
    mileage = int(mileage_match.group(1)) * 1000 if mileage_match else None

    warnings = [
        "Bu çıktı yalnızca başlangıç kural motorudur; usta onayı olmadan kaydedilmemelidir.",
    ]
    if not dtc_codes:
        warnings.append("Metinde doğrulanabilir OBD-II kodu bulunamadı.")

    return schemas.ExtractionPreview(
        provider="demo-rules-v1",
        raw_text=text,
        dtc_codes=dtc_codes,
        mileage=mileage,
        probable_fields={
            "customer_complaint": text,
            "symptoms": [],
            "diagnosis": None,
            "actions": [],
            "result": None,
        },
        warnings=warnings,
    )


def search_cases(db: Session, payload: schemas.CaseSearchRequest) -> list[tuple[models.WorkOrder, str]]:
    terms = [term for term in re.split(r"\s+", payload.query.strip()) if len(term) > 1]
    query: Select[tuple[models.WorkOrder]] = (
        select(models.WorkOrder)
        .options(selectinload(models.WorkOrder.dtc_codes), selectinload(models.WorkOrder.vehicle))
        .order_by(models.WorkOrder.created_at.desc())
    )

    filters = []
    for term in terms[:8]:
        filters.append(models.WorkOrder.search_text.ilike(f"%{term}%"))

    if payload.dtc_code:
        normalized_code = payload.dtc_code.strip().upper()
        query = query.join(models.WorkOrder.dtc_codes)
        filters.append(models.DtcCode.code == normalized_code)

    if filters:
        query = query.where(or_(*filters))

    work_orders = db.scalars(query.limit(payload.limit)).unique().all()
    results = []
    for work_order in work_orders:
        matched_codes = {code.code for code in work_order.dtc_codes}
        if payload.dtc_code and payload.dtc_code.upper() in matched_codes:
            reason = f"OBD-II kodu eşleşti: {payload.dtc_code.upper()}"
        else:
            reason = "Şikâyet veya servis metninde anahtar kelime eşleşmesi"
        results.append((work_order, reason))
    return results

