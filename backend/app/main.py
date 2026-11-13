import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app import ml, models, schemas, services
from app.config import settings
from app.database import get_db

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_work_order_or_404(work_order_id: uuid.UUID, db: Session) -> models.WorkOrder:
    work_order = db.scalar(
        select(models.WorkOrder)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .where(models.WorkOrder.id == work_order_id)
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="İş emri bulunamadı")
    return work_order


@app.get(f"{settings.api_prefix}/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.post(
    f"{settings.api_prefix}/vehicles",
    response_model=schemas.VehicleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(payload: schemas.VehicleCreate, db: Session = Depends(get_db)) -> models.Vehicle:
    vehicle = models.Vehicle(**payload.model_dump())
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Anonim araç kodu zaten kullanılıyor") from exc
    db.refresh(vehicle)
    return vehicle


@app.get(f"{settings.api_prefix}/vehicles", response_model=list[schemas.VehicleRead])
def list_vehicles(db: Session = Depends(get_db)) -> list[models.Vehicle]:
    return list(db.scalars(select(models.Vehicle).order_by(models.Vehicle.created_at.desc())).all())


@app.get(f"{settings.api_prefix}/vehicles/{{vehicle_id}}", response_model=schemas.VehicleRead)
def get_vehicle(vehicle_id: uuid.UUID, db: Session = Depends(get_db)) -> models.Vehicle:
    vehicle = db.get(models.Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")
    return vehicle


@app.patch(f"{settings.api_prefix}/vehicles/{{vehicle_id}}", response_model=schemas.VehicleRead)
def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: schemas.VehicleUpdate,
    db: Session = Depends(get_db),
) -> models.Vehicle:
    vehicle = db.get(models.Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.post(
    f"{settings.api_prefix}/work-orders",
    response_model=schemas.WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order(payload: schemas.WorkOrderCreate, db: Session = Depends(get_db)) -> models.WorkOrder:
    if db.get(models.Vehicle, payload.vehicle_id) is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")

    data = payload.model_dump(exclude={"dtc_codes"})
    work_order = models.WorkOrder(**data, search_text=services.build_search_text(payload))
    work_order.dtc_codes = [
        models.DtcCode(
            code=item.code,
            description=item.description or services.dtc_description(item.code),
        )
        for item in payload.dtc_codes
    ]
    services.refresh_work_order_embedding(work_order)
    db.add(work_order)
    if payload.voice_transcript:
        db.flush()
        preview = services.extract_preview(payload.voice_transcript)
        db.add(
            models.AIExtraction(
                work_order_id=work_order.id,
                provider=preview.provider,
                raw_text=payload.voice_transcript,
                extracted_json=preview.model_dump(mode="json"),
                confirmed=payload.approved_by_mechanic,
            )
        )
    db.commit()

    return db.scalar(
        select(models.WorkOrder)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .where(models.WorkOrder.id == work_order.id)
    )


@app.get(f"{settings.api_prefix}/work-orders", response_model=list[schemas.WorkOrderRead])
def list_work_orders(db: Session = Depends(get_db)) -> list[models.WorkOrder]:
    query = (
        select(models.WorkOrder)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .order_by(models.WorkOrder.created_at.desc())
    )
    return list(db.scalars(query).unique().all())


@app.get(f"{settings.api_prefix}/work-orders/{{work_order_id}}", response_model=schemas.WorkOrderRead)
def get_work_order(work_order_id: uuid.UUID, db: Session = Depends(get_db)) -> models.WorkOrder:
    return get_work_order_or_404(work_order_id, db)


@app.patch(f"{settings.api_prefix}/work-orders/{{work_order_id}}", response_model=schemas.WorkOrderRead)
def update_work_order(
    work_order_id: uuid.UUID,
    payload: schemas.WorkOrderUpdate,
    db: Session = Depends(get_db),
) -> models.WorkOrder:
    work_order = get_work_order_or_404(work_order_id, db)
    update_data = payload.model_dump(exclude_unset=True, exclude={"dtc_codes"})

    if update_data.get("customer_complaint", "not-set") is None:
        raise HTTPException(status_code=422, detail="Müşteri şikâyeti boş bırakılamaz")
    if update_data.get("status", "not-set") is None:
        raise HTTPException(status_code=422, detail="İş emri durumu boş bırakılamaz")

    for field, value in update_data.items():
        setattr(work_order, field, value)

    if payload.dtc_codes is not None:
        work_order.dtc_codes = [
            models.DtcCode(
                code=item.code,
                description=item.description or services.dtc_description(item.code),
            )
            for item in payload.dtc_codes
        ]

    work_order.search_text = services.build_search_text_from_order(work_order)
    services.refresh_work_order_embedding(work_order)
    db.commit()
    return get_work_order_or_404(work_order_id, db)


@app.get(f"{settings.api_prefix}/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db)) -> schemas.DashboardSummary:
    total_vehicles = db.scalar(select(func.count()).select_from(models.Vehicle)) or 0
    status_rows = db.execute(
        select(models.WorkOrder.status, func.count()).group_by(models.WorkOrder.status)
    ).all()
    status_counts = {status_name: count for status_name, count in status_rows}
    total_work_orders = sum(status_counts.values())
    completed_work_orders = status_counts.get("completed", 0)
    open_work_orders = total_work_orders - completed_work_orders - status_counts.get("cancelled", 0)
    approved_cases = (
        db.scalar(
            select(func.count())
            .select_from(models.WorkOrder)
            .where(models.WorkOrder.approved_by_mechanic.is_(True))
        )
        or 0
    )
    recent_query = (
        select(models.WorkOrder)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .order_by(models.WorkOrder.created_at.desc())
        .limit(6)
    )
    recent_work_orders = list(db.scalars(recent_query).unique().all())

    return schemas.DashboardSummary(
        total_vehicles=total_vehicles,
        total_work_orders=total_work_orders,
        open_work_orders=open_work_orders,
        completed_work_orders=completed_work_orders,
        approved_cases=approved_cases,
        status_counts=status_counts,
        recent_work_orders=[schemas.WorkOrderRead.model_validate(item) for item in recent_work_orders],
    )


@app.post(f"{settings.api_prefix}/ai/extract-preview", response_model=schemas.ExtractionPreview)
def preview_extraction(payload: schemas.ExtractionRequest) -> schemas.ExtractionPreview:
    return services.extract_preview(payload.text)


@app.get(f"{settings.api_prefix}/ai/status", response_model=schemas.AIRuntimeStatus)
def ai_runtime_status() -> schemas.AIRuntimeStatus:
    return schemas.AIRuntimeStatus.model_validate(ml.runtime_status())


@app.post(f"{settings.api_prefix}/audio/transcribe", response_model=schemas.TranscriptionResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    retain_audio: bool = Form(default=False),
) -> schemas.TranscriptionResponse:
    content_type = (audio.content_type or "").split(";", maxsplit=1)[0].lower()
    suffix_by_type = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
        "audio/flac": ".flac",
    }
    if content_type not in suffix_by_type:
        raise HTTPException(
            status_code=415,
            detail="Desteklenen ses türleri: WebM, WAV, MP3, M4A, OGG ve FLAC",
        )

    storage = Path(settings.audio_storage_path)
    storage.mkdir(parents=True, exist_ok=True)
    target = storage / f"{uuid.uuid4().hex}{suffix_by_type[content_type]}"
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    total_size = 0

    try:
        with target.open("wb") as output:
            while chunk := await audio.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Ses kaydı en fazla {settings.max_audio_size_mb} MB olabilir",
                    )
                output.write(chunk)

        result = await run_in_threadpool(ml.transcribe_audio, target)
        if not result.text:
            raise HTTPException(status_code=422, detail="Ses kaydında konuşma algılanamadı")
        return schemas.TranscriptionResponse(
            transcript=result.text,
            language=result.language,
            language_probability=result.language_probability,
            duration_seconds=result.duration_seconds,
            provider=result.provider,
            audio_retained=retain_audio,
        )
    except ml.TranscriptionUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        await audio.close()
        if not retain_audio:
            target.unlink(missing_ok=True)


@app.post(f"{settings.api_prefix}/cases/search", response_model=list[schemas.CaseSearchResult])
def search_cases(payload: schemas.CaseSearchRequest, db: Session = Depends(get_db)) -> list[schemas.CaseSearchResult]:
    results = services.search_cases(db, payload)
    return [
        schemas.CaseSearchResult(
            work_order=schemas.WorkOrderRead.model_validate(match.work_order),
            vehicle=schemas.VehicleRead.model_validate(match.work_order.vehicle),
            match_reason=match.reason,
            similarity_score=round(match.score, 4),
            search_method=match.method,
        )
        for match in results
    ]

