import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class DtcCodeCreate(BaseModel):
    code: str = Field(min_length=5, max_length=8)
    description: str | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not (len(normalized) == 5 and normalized[0] in "PBCU" and normalized[1:].isdigit()):
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
    status: str = "draft"
    approved_by_mechanic: bool = False
    voice_transcript: str | None = None
    dtc_codes: list[DtcCodeCreate] = []


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    customer_complaint: str
    symptoms: str | None
    diagnosis: str | None
    actions: str | None
    result: str | None
    status: str
    approved_by_mechanic: bool
    voice_transcript: str | None
    created_at: datetime
    dtc_codes: list[DtcCodeRead]


class ExtractionRequest(BaseModel):
    text: str = Field(min_length=5)


class ExtractionPreview(BaseModel):
    provider: str
    raw_text: str
    dtc_codes: list[str]
    mileage: int | None
    probable_fields: dict[str, str | int | list[str] | None]
    warnings: list[str]


class CaseSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    dtc_code: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class CaseSearchResult(BaseModel):
    work_order: WorkOrderRead
    vehicle: VehicleRead
    match_reason: str

