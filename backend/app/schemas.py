import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


WorkOrderStatus = Literal[
    "draft",
    "inspection",
    "repairing",
    "waiting_parts",
    "completed",
    "cancelled",
]
AppointmentStatus = Literal[
    "scheduled",
    "confirmed",
    "checked_in",
    "in_service",
    "completed",
    "cancelled",
    "no_show",
]
ReminderStatus = Literal["pending", "completed", "dismissed"]
ReminderDueState = Literal["overdue", "due_soon", "upcoming", "completed", "dismissed"]
InspectionStatus = Literal["draft", "in_progress", "completed"]
InspectionCondition = Literal["not_checked", "good", "attention", "critical"]
Language = Literal["tr", "en"]


class RegistrationRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    workshop_name: str | None = Field(default=None, max_length=160)
    email: EmailStr
    phone_country_code: str = Field(pattern=r"^\+[0-9]{1,4}$")
    phone_number: str = Field(min_length=6, max_length=15, pattern=r"^[0-9]+$")
    preferred_language: Language = "tr"
    privacy_accepted: Literal[True]
    terms_accepted: Literal[True]
    marketing_consent: bool = False

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Ad soyad en az iki karakter olmalıdır")
        return normalized

    @field_validator("workshop_name")
    @classmethod
    def strip_workshop_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class OTPRequest(BaseModel):
    email: EmailStr
    language: Language = "tr"


class OTPVerify(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    language: Language = "tr"


class AuthUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    workshop_name: str | None
    phone_country_code: str
    phone_number: str
    preferred_language: Language
    marketing_consent: bool
    created_at: datetime
    privacy_accepted_at: datetime
    terms_accepted_at: datetime


class AuthResponse(BaseModel):
    user: AuthUser
    mailpit_url: str | None = None


class AuthMessage(BaseModel):
    message: str
    retry_after: int | None = None
    mailpit_url: str | None = None
    local_code: str | None = None


class UserPreferencesUpdate(BaseModel):
    preferred_language: Language


class UserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    workshop_name: str | None = Field(default=None, max_length=160)
    phone_country_code: str = Field(pattern=r"^\+[0-9]{1,4}$")
    phone_number: str = Field(min_length=6, max_length=15, pattern=r"^[0-9]+$")
    marketing_consent: bool = False

    @field_validator("full_name")
    @classmethod
    def normalize_profile_name(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("Ad soyad en az iki karakter olmalıdır")
        return normalized

    @field_validator("workshop_name")
    @classmethod
    def normalize_profile_workshop(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    event_data: dict
    created_at: datetime


class VehicleCreate(BaseModel):
    anonymous_code: str = Field(min_length=3, max_length=32)
    brand: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    model_year: int | None = Field(default=None, ge=1950, le=2100)
    engine: str | None = Field(default=None, max_length=120)
    fuel_type: str | None = Field(default=None, max_length=40)
    mileage: int | None = Field(default=None, ge=0, le=5_000_000)


class VehicleRead(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class VehicleUpdate(BaseModel):
    brand: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    model_year: int | None = Field(default=None, ge=1950, le=2100)
    engine: str | None = Field(default=None, max_length=120)
    fuel_type: str | None = Field(default=None, max_length=40)
    mileage: int | None = Field(default=None, ge=0, le=5_000_000)


class DtcCodeCreate(BaseModel):
    code: str = Field(min_length=5, max_length=8)
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not re.fullmatch(r"[PBCU][0-3][0-9A-F]{3}", normalized):
            raise ValueError("OBD-II kodu P0299 benzeri beş karakterli olmalıdır")
        return normalized


class DtcCodeRead(DtcCodeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class WorkOrderCreate(BaseModel):
    vehicle_id: uuid.UUID
    customer_complaint: str = Field(min_length=3)
    symptoms: str | None = None
    diagnosis: str | None = None
    actions: str | None = None
    result: str | None = None
    status: WorkOrderStatus = "draft"
    approved_by_mechanic: bool = False
    voice_transcript: str | None = None
    dtc_codes: list[DtcCodeCreate] = Field(default_factory=list)


class WorkOrderUpdate(BaseModel):
    customer_complaint: str | None = Field(default=None, min_length=3)
    symptoms: str | None = None
    diagnosis: str | None = None
    actions: str | None = None
    result: str | None = None
    status: WorkOrderStatus | None = None
    approved_by_mechanic: bool | None = None
    voice_transcript: str | None = None
    dtc_codes: list[DtcCodeCreate] | None = None


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    customer_complaint: str
    symptoms: str | None
    diagnosis: str | None
    actions: str | None
    result: str | None
    status: WorkOrderStatus
    approved_by_mechanic: bool
    voice_transcript: str | None
    created_at: datetime
    dtc_codes: list[DtcCodeRead]


class AppointmentCreate(BaseModel):
    vehicle_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime
    service_type: str = Field(min_length=2, max_length=120)
    customer_complaint: str = Field(min_length=3, max_length=2_000)
    status: AppointmentStatus = "scheduled"
    assigned_technician: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_interval(self) -> "AppointmentCreate":
        both_aware = self.scheduled_start.tzinfo is not None and self.scheduled_end.tzinfo is not None
        both_naive = self.scheduled_start.tzinfo is None and self.scheduled_end.tzinfo is None
        if (both_aware or both_naive) and self.scheduled_end <= self.scheduled_start:
            raise ValueError("Randevu bitiş saati başlangıç saatinden sonra olmalıdır")
        return self


class AppointmentUpdate(BaseModel):
    vehicle_id: uuid.UUID | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    service_type: str | None = Field(default=None, min_length=2, max_length=120)
    customer_complaint: str | None = Field(default=None, min_length=3, max_length=2_000)
    status: AppointmentStatus | None = None
    assigned_technician: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2_000)


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    scheduled_start: datetime
    scheduled_end: datetime
    service_type: str
    customer_complaint: str
    status: AppointmentStatus
    assigned_technician: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MaintenanceReminderCreate(BaseModel):
    vehicle_id: uuid.UUID
    title: str = Field(min_length=2, max_length=160)
    due_date: date | None = None
    due_mileage: int | None = Field(default=None, ge=0, le=5_000_000)
    notes: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_due_target(self) -> "MaintenanceReminderCreate":
        if self.due_date is None and self.due_mileage is None:
            raise ValueError("Bakım hatırlatması için tarih veya kilometre girilmelidir")
        return self


class MaintenanceReminderUpdate(BaseModel):
    vehicle_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=2, max_length=160)
    due_date: date | None = None
    due_mileage: int | None = Field(default=None, ge=0, le=5_000_000)
    status: ReminderStatus | None = None
    notes: str | None = Field(default=None, max_length=2_000)


class MaintenanceReminderRead(BaseModel):
    id: uuid.UUID
    vehicle_id: uuid.UUID
    title: str
    due_date: date | None
    due_mileage: int | None
    status: ReminderStatus
    due_state: ReminderDueState
    notes: str | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ScheduleSummary(BaseModel):
    today_appointments: int
    upcoming_appointments: int
    active_appointments: int
    overdue_reminders: int
    due_soon_reminders: int


class InspectionTemplateItemRead(BaseModel):
    category: str
    item_key: str
    label: str
    position: int


class InspectionItemUpdate(BaseModel):
    item_key: str = Field(min_length=2, max_length=80)
    condition: InspectionCondition
    measurement: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1_000)
    resolved: bool = False


class InspectionReportUpdate(BaseModel):
    status: InspectionStatus | None = None
    odometer: int | None = Field(default=None, ge=0, le=5_000_000)
    technician_name: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=2_000)
    mechanic_approved: bool | None = None
    items: list[InspectionItemUpdate] | None = None

    @field_validator("items")
    @classmethod
    def unique_item_keys(
        cls, value: list[InspectionItemUpdate] | None
    ) -> list[InspectionItemUpdate] | None:
        if value is not None and len({item.item_key for item in value}) != len(value):
            raise ValueError("Aynı kontrol maddesi birden fazla kez gönderilemez")
        return value


class InspectionItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    item_key: str
    label: str
    condition: InspectionCondition
    measurement: str | None
    notes: str | None
    resolved: bool
    position: int


class InspectionReportRead(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    status: InspectionStatus
    odometer: int | None
    technician_name: str | None
    notes: str | None
    mechanic_approved: bool
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[InspectionItemRead]
    health_score: int
    checked_count: int
    total_count: int
    attention_count: int
    critical_count: int
    unresolved_critical_count: int


class ExtractionRequest(BaseModel):
    text: str = Field(min_length=5)


class ExtractionPreview(BaseModel):
    provider: str
    raw_text: str
    dtc_codes: list[str]
    dtc_details: list[DtcCodeCreate] = Field(default_factory=list)
    mileage: int | None
    probable_fields: dict[str, str | int | list[str] | None]
    warnings: list[str]


class CaseSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    dtc_code: str | None = None
    limit: int = Field(default=5, ge=1, le=20)
    search_mode: Literal["hybrid", "keyword", "semantic"] = "hybrid"
    approved_only: bool = False


class CaseSearchResult(BaseModel):
    work_order: WorkOrderRead
    vehicle: VehicleRead
    match_reason: str
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    search_method: Literal["keyword", "semantic", "hybrid", "dtc"] = "keyword"


EvaluationMode = Literal["keyword", "semantic", "hybrid"]


class EvidenceRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    dtc_code: str | None = Field(default=None, max_length=8)
    search_mode: EvaluationMode = "hybrid"


class EvidenceResponse(BaseModel):
    summary: str
    confidence: Literal["insufficient", "low", "medium", "high"]
    confidence_score: float = Field(ge=0, le=1)
    suggested_checks: list[str]
    limitations: list[str]
    evidence: list[CaseSearchResult]


class EvaluationQueryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    query_text: str = Field(min_length=3, max_length=2000)
    dtc_code: str | None = Field(default=None, max_length=8)
    expected_work_order_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "query_text")
    @classmethod
    def normalize_evaluation_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("dtc_code")
    @classmethod
    def normalize_evaluation_dtc(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().upper()
        if not re.fullmatch(r"[PBCU][0-3][0-9A-F]{3}", normalized):
            raise ValueError("OBD-II kodu P0299 benzeri beş karakterli olmalıdır")
        return normalized


class EvaluationQueryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    query_text: str
    dtc_code: str | None
    expected_work_order_id: uuid.UUID
    notes: str | None
    created_at: datetime


class EvaluationRunRequest(BaseModel):
    modes: list[EvaluationMode] = Field(min_length=1, max_length=3)
    top_k: int = Field(default=5, ge=1, le=10)

    @field_validator("modes")
    @classmethod
    def unique_modes(cls, value: list[EvaluationMode]) -> list[EvaluationMode]:
        return list(dict.fromkeys(value))


class EvaluationModeMetrics(BaseModel):
    mode: EvaluationMode
    hit_rate: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
    avg_latency_ms: float = Field(ge=0)
    hits: int = Field(ge=0)
    query_count: int = Field(ge=0)


class EvaluationDetail(BaseModel):
    query_id: uuid.UUID
    query_name: str
    expected_work_order_id: uuid.UUID
    mode: EvaluationMode
    rank: int | None
    reciprocal_rank: float = Field(ge=0, le=1)
    latency_ms: float = Field(ge=0)
    result_work_order_ids: list[uuid.UUID]


class EvaluationRunRead(BaseModel):
    id: uuid.UUID
    modes: list[EvaluationMode]
    top_k: int
    query_count: int
    metrics: list[EvaluationModeMetrics]
    details: list[EvaluationDetail]
    best_mode: EvaluationMode | None
    created_at: datetime


class EvaluationSummary(BaseModel):
    query_count: int
    run_count: int
    best_mode: EvaluationMode | None
    best_hit_rate: float = Field(ge=0, le=1)
    latest_run_at: datetime | None


class TranscriptionResponse(BaseModel):
    transcript: str
    language: str
    language_probability: float = Field(ge=0, le=1)
    duration_seconds: float = Field(ge=0)
    provider: str
    audio_retained: bool


class AIRuntimeStatus(BaseModel):
    embedding_model: str
    embedding_loaded: bool
    embedding_error: str | None
    whisper_model: str
    whisper_loaded: bool
    whisper_error: str | None


class DashboardSummary(BaseModel):
    total_vehicles: int
    total_work_orders: int
    open_work_orders: int
    completed_work_orders: int
    approved_cases: int
    status_counts: dict[str, int]
    recent_work_orders: list[WorkOrderRead]


InvoiceItemType = Literal["part", "labor", "other"]
InvoiceStatus = Literal["issued", "partially_paid", "paid", "cancelled"]
PaymentMethod = Literal["cash", "card_pos", "test_card", "bank_transfer", "other"]
EstimateStatus = Literal["draft", "sent", "approved", "rejected", "expired", "converted"]


class InvoiceLineCreate(BaseModel):
    item_type: InvoiceItemType
    inventory_part_id: uuid.UUID | None = None
    description: str = Field(min_length=2, max_length=240)
    quantity: Decimal = Field(gt=0, le=100_000, decimal_places=2)
    unit_price: Decimal = Field(ge=0, le=100_000_000, decimal_places=2)


class EstimateCreate(BaseModel):
    line_items: list[InvoiceLineCreate] = Field(min_length=1, max_length=100)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, le=100_000_000, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("20"), ge=0, le=100, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    valid_until: date


class EstimateUpdate(BaseModel):
    line_items: list[InvoiceLineCreate] | None = Field(default=None, min_length=1, max_length=100)
    discount_amount: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    valid_until: date | None = None


class EstimateLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_part_id: uuid.UUID | None
    item_type: InvoiceItemType
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    position: int


class EstimateRead(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    converted_invoice_id: uuid.UUID | None
    estimate_number: str
    version: int
    status: EstimateStatus
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None
    valid_until: date
    approval_expires_at: datetime | None
    responded_at: datetime | None
    response_note: str | None
    created_at: datetime
    updated_at: datetime
    line_items: list[EstimateLineRead]


class EstimateSendResponse(BaseModel):
    estimate: EstimateRead
    approval_url: str
    expires_at: datetime


class EstimatePublicAccess(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class EstimatePublicDecision(EstimatePublicAccess):
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=1000)


class EstimatePublicRead(BaseModel):
    id: uuid.UUID
    estimate_number: str
    status: EstimateStatus
    workshop_name: str
    vehicle_code: str
    vehicle_description: str
    complaint: str
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: str | None
    valid_until: date
    approval_expires_at: datetime | None
    responded_at: datetime | None
    response_note: str | None
    line_items: list[EstimateLineRead]


class EstimateConvertRequest(BaseModel):
    due_date: date | None = None


class InvoiceCreate(BaseModel):
    line_items: list[InvoiceLineCreate] = Field(min_length=1, max_length=100)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, le=100_000_000, decimal_places=2)
    tax_rate: Decimal = Field(default=Decimal("20"), ge=0, le=100, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    due_date: date | None = None


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    inventory_part_id: uuid.UUID | None
    item_type: InvoiceItemType
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    method: PaymentMethod
    reference: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    reference: str | None
    notes: str | None
    received_at: datetime


class InvoiceRead(BaseModel):
    id: uuid.UUID
    work_order_id: uuid.UUID
    invoice_number: str
    status: InvoiceStatus
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    notes: str | None
    issued_at: datetime
    due_date: date | None
    created_at: datetime
    line_items: list[InvoiceLineRead]
    payments: list[PaymentRead]


class FinanceSummary(BaseModel):
    invoiced_total: Decimal
    collected_total: Decimal
    outstanding_total: Decimal
    total_invoices: int
    paid_invoices: int
    partially_paid_invoices: int
    overdue_invoices: int


CardChallengeStatus = Literal["pending", "succeeded", "failed", "expired"]


class CardPaymentStart(BaseModel):
    amount: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    card_last4: str = Field(pattern=r"^\d{4}$")


class CardPaymentStartResponse(BaseModel):
    challenge_id: uuid.UUID
    redirect_url: str
    expires_at: datetime


class CardChallengeAccess(BaseModel):
    token: str = Field(min_length=40, max_length=200)


class CardChallengeVerify(CardChallengeAccess):
    code: str = Field(pattern=r"^\d{6}$")


class CardChallengeRead(BaseModel):
    challenge_id: uuid.UUID
    invoice_id: uuid.UUID
    invoice_number: str
    amount: Decimal
    currency: str
    card_last4: str
    status: CardChallengeStatus
    expires_at: datetime
    attempts_remaining: int


class CardChallengeVerifyResponse(BaseModel):
    status: CardChallengeStatus
    message: str
    attempts_remaining: int
    redirect_url: str | None = None


StockMovementType = Literal["initial", "stock_in", "stock_out", "invoice_sale"]


class InventoryPartCreate(BaseModel):
    sku: str = Field(min_length=2, max_length=48, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str = Field(min_length=2, max_length=160)
    brand: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    unit: str = Field(default="piece", min_length=1, max_length=20)
    initial_quantity: Decimal = Field(default=Decimal("0"), ge=0, le=100_000_000, decimal_places=2)
    low_stock_threshold: Decimal = Field(default=Decimal("1"), ge=0, le=100_000_000, decimal_places=2)
    purchase_price: Decimal = Field(default=Decimal("0"), ge=0, le=100_000_000, decimal_places=2)
    sale_price: Decimal = Field(default=Decimal("0"), ge=0, le=100_000_000, decimal_places=2)

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("name", "unit")
    @classmethod
    def strip_required_inventory_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Alan boş bırakılamaz")
        return normalized

    @field_validator("brand", "category")
    @classmethod
    def strip_optional_inventory_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class InventoryPartUpdate(BaseModel):
    sku: str | None = Field(default=None, min_length=2, max_length=48, pattern=r"^[A-Za-z0-9._/-]+$")
    name: str | None = Field(default=None, min_length=2, max_length=160)
    brand: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    low_stock_threshold: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    purchase_price: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    sale_price: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    active: bool | None = None

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_optional_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("name", "unit")
    @classmethod
    def strip_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Alan boş bırakılamaz")
        return normalized

    @field_validator("brand", "category")
    @classmethod
    def strip_optional_part_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class InventoryPartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str
    brand: str | None
    category: str | None
    unit: str
    stock_quantity: Decimal
    low_stock_threshold: Decimal
    purchase_price: Decimal
    sale_price: Decimal
    active: bool
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime


class StockMovementCreate(BaseModel):
    movement_type: Literal["stock_in", "stock_out"]
    quantity: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    part_id: uuid.UUID
    movement_type: StockMovementType
    quantity_delta: Decimal
    balance_after: Decimal
    reference_type: str | None
    reference_id: uuid.UUID | None
    notes: str | None
    created_at: datetime


class InventorySummary(BaseModel):
    total_parts: int
    low_stock_parts: int
    out_of_stock_parts: int
    inventory_cost_value: Decimal
    inventory_sale_value: Decimal

