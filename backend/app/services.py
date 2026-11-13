import re

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app import models, schemas

DTC_PATTERN = re.compile(r"\b[PBCU][0-3][0-9A-F]{3}\b", re.IGNORECASE)
THOUSAND_MILEAGE_PATTERN = re.compile(r"\b(\d{1,3})\s*bin\b", re.IGNORECASE)
KM_MILEAGE_PATTERN = re.compile(
    r"\b(\d{1,3}(?:[.\s]\d{3})+|\d{4,7})\s*(?:km|kilometre)\b",
    re.IGNORECASE,
)

DTC_DESCRIPTIONS = {
    "P0101": "Hava akış sensörü (MAF) aralık/performans sorunu",
    "P0171": "Sistem çok fakir karışım algıladı",
    "P0299": "Turbo/süperşarj basıncı beklenenden düşük",
    "P0300": "Rastgele veya birden fazla silindirde ateşleme hatası",
    "P0401": "EGR akışı yetersiz",
    "P0420": "Katalizör verimliliği eşik değerinin altında",
    "P0562": "Sistem voltajı düşük",
    "P2002": "Dizel partikül filtresi verimliliği eşik değerinin altında",
    "P2453": "DPF basınç sensörü devre aralık/performans sorunu",
    "P0A80": "Hibrit batarya paketini değiştir uyarısı",
}

SYMPTOM_PATTERNS = {
    "çekiş düşüklüğü": ("çekişten düş", "çekiş düş", "güç kayb", "gitmiyor"),
    "düzensiz rölanti": ("rölanti", "rolanti"),
    "tekleme": ("tekliyor", "tekleme"),
    "zor çalışma": ("zor çalış", "geç çalış", "marş alm"),
    "hararet": ("hararet", "ısınma"),
    "titreşim": ("titriyor", "titreşim"),
    "anormal ses": ("ses geliyor", "uğultu", "vuruntu", "tıkırtı"),
    "egzoz dumanı": ("duman", "is atıyor"),
    "yakıt tüketimi artışı": ("çok yak", "yakıt tüketimi"),
}

ACTION_KEYWORDS = (
    "değiştirildi",
    "değişti",
    "temizlendi",
    "onarım",
    "tamir",
    "kontrol edildi",
    "söküldü",
    "takıldı",
)


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


def build_search_text_from_order(work_order: models.WorkOrder) -> str:
    values = [
        work_order.customer_complaint,
        work_order.symptoms,
        work_order.diagnosis,
        work_order.actions,
        work_order.result,
        work_order.voice_transcript,
        " ".join(item.code for item in work_order.dtc_codes),
    ]
    return " ".join(value.strip() for value in values if value and value.strip())


def dtc_description(code: str) -> str | None:
    return DTC_DESCRIPTIONS.get(code.strip().upper())


def _extract_mileage(text: str) -> int | None:
    thousand_match = THOUSAND_MILEAGE_PATTERN.search(text)
    if thousand_match:
        return int(thousand_match.group(1)) * 1000

    km_match = KM_MILEAGE_PATTERN.search(text)
    if not km_match:
        return None
    return int(re.sub(r"[.\s]", "", km_match.group(1)))


def _extract_symptoms(text: str) -> list[str]:
    normalized = text.casefold()
    return [
        label
        for label, patterns in SYMPTOM_PATTERNS.items()
        if any(pattern in normalized for pattern in patterns)
    ]


def _extract_actions(text: str) -> list[str]:
    sentences = [part.strip() for part in re.split(r"[.!?;\n]+", text) if part.strip()]
    return [
        sentence
        for sentence in sentences
        if any(keyword in sentence.casefold() for keyword in ACTION_KEYWORDS)
    ]


def extract_preview(text: str) -> schemas.ExtractionPreview:
    dtc_codes = sorted({match.upper() for match in DTC_PATTERN.findall(text)})
    mileage = _extract_mileage(text)
    symptoms = _extract_symptoms(text)
    actions = _extract_actions(text)
    dtc_details = [
        schemas.DtcCodeCreate(code=code, description=dtc_description(code)) for code in dtc_codes
    ]

    warnings = [
        "Bu çıktı yalnızca başlangıç kural motorudur; usta onayı olmadan kaydedilmemelidir.",
    ]
    if not dtc_codes:
        warnings.append("Metinde doğrulanabilir OBD-II kodu bulunamadı.")
    if dtc_codes and any(item.description is None for item in dtc_details):
        warnings.append("Bazı OBD-II kodlarının açıklaması yerel bilgi tabanında bulunamadı.")

    return schemas.ExtractionPreview(
        provider="turkish-rules-v2",
        raw_text=text,
        dtc_codes=dtc_codes,
        dtc_details=dtc_details,
        mileage=mileage,
        probable_fields={
            "customer_complaint": text,
            "symptoms": symptoms,
            "diagnosis": None,
            "actions": actions,
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
        query = query.where(models.DtcCode.code == normalized_code)

    if filters:
        query = query.where(or_(*filters))

    work_orders = db.scalars(query.limit(payload.limit)).unique().all()
    results = []
    for work_order in work_orders:
        matched_codes = {code.code for code in work_order.dtc_codes}
        if payload.dtc_code and payload.dtc_code.upper() in matched_codes:
            reason = f"OBD-II kodu eşleşti: {payload.dtc_code.upper()}"
        else:
            matched_terms = [
                term for term in terms if term.casefold() in (work_order.search_text or "").casefold()
            ]
            suffix = f": {', '.join(matched_terms[:3])}" if matched_terms else ""
            reason = f"Şikâyet veya servis metninde anahtar kelime eşleşmesi{suffix}"
        results.append((work_order, reason))
    return results

