import re
import uuid
from dataclasses import dataclass

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, selectinload

from app import ml, models, schemas

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


@dataclass
class CaseMatch:
    work_order: models.WorkOrder
    reason: str
    score: float
    method: str


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


def refresh_work_order_embedding(work_order: models.WorkOrder) -> str:
    vector, provider = ml.embed_text(build_search_text_from_order(work_order), kind="passage")
    work_order.embedding = vector
    return provider


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


def _base_case_query(
    payload: schemas.CaseSearchRequest,
    user_id: uuid.UUID,
) -> Select[tuple[models.WorkOrder]]:
    query: Select[tuple[models.WorkOrder]] = (
        select(models.WorkOrder)
        .join(models.WorkOrder.vehicle)
        .options(
            selectinload(models.WorkOrder.dtc_codes),
            selectinload(models.WorkOrder.vehicle),
        )
        .where(models.Vehicle.owner_id == user_id)
    )
    if payload.approved_only:
        query = query.where(models.WorkOrder.approved_by_mechanic.is_(True))
    if payload.dtc_code:
        query = query.join(models.WorkOrder.dtc_codes).where(
            models.DtcCode.code == payload.dtc_code.strip().upper()
        )
    return query


def search_cases(
    db: Session,
    payload: schemas.CaseSearchRequest,
    user_id: uuid.UUID,
) -> list[CaseMatch]:
    terms = [term for term in re.split(r"\s+", payload.query.strip()) if len(term) > 1]
    matches: dict[object, CaseMatch] = {}
    candidate_limit = max(payload.limit * 3, 12)

    if payload.search_mode in {"keyword", "hybrid"}:
        keyword_query = _base_case_query(payload, user_id).order_by(
            models.WorkOrder.created_at.desc()
        )
        filters = [models.WorkOrder.search_text.ilike(f"%{term}%") for term in terms[:8]]
        if filters:
            keyword_query = keyword_query.where(or_(*filters))

        work_orders = db.scalars(keyword_query.limit(candidate_limit)).unique().all()
        for work_order in work_orders:
            normalized_text = (work_order.search_text or "").casefold()
            matched_terms = [term for term in terms if term.casefold() in normalized_text]
            matched_codes = {code.code for code in work_order.dtc_codes}
            dtc_match = bool(
                payload.dtc_code and payload.dtc_code.strip().upper() in matched_codes
            )
            overlap = len(matched_terms) / max(len(terms), 1)
            score = min(0.95, (0.55 + 0.35 * overlap) if not dtc_match else 0.98)
            if dtc_match:
                reason = f"OBD-II kodu eşleşti: {payload.dtc_code.strip().upper()}"
                method = "dtc"
            else:
                suffix = f": {', '.join(matched_terms[:3])}" if matched_terms else ""
                reason = f"Servis metninde anahtar kelime eşleşmesi{suffix}"
                method = "keyword"
            matches[work_order.id] = CaseMatch(work_order, reason, score, method)

    if payload.search_mode in {"semantic", "hybrid"}:
        query_vector, _provider = ml.embed_text(payload.query, kind="query")
        distance = models.WorkOrder.embedding.cosine_distance(query_vector).label("distance")
        semantic_query = _base_case_query(payload, user_id).add_columns(distance).where(
            models.WorkOrder.embedding.is_not(None)
        )
        semantic_query = semantic_query.order_by(distance).limit(candidate_limit)
        semantic_rows = db.execute(semantic_query).unique().all()

        for work_order, distance_value in semantic_rows:
            similarity = max(0.0, min(1.0, 1.0 - float(distance_value)))
            if similarity < 0.15:
                continue
            existing = matches.get(work_order.id)
            if existing:
                existing.score = min(1.0, 0.45 * existing.score + 0.55 * similarity + 0.05)
                existing.method = "hybrid"
                existing.reason = f"{existing.reason}; anlamsal benzerlik %{similarity * 100:.0f}"
            else:
                matches[work_order.id] = CaseMatch(
                    work_order=work_order,
                    reason=f"Servis anlatımıyla anlamsal benzerlik %{similarity * 100:.0f}",
                    score=similarity,
                    method="semantic",
                )

    return sorted(matches.values(), key=lambda item: item.score, reverse=True)[: payload.limit]

