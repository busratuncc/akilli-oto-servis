import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app import auth, ml, models, schemas, services
from app.config import settings
from app.database import SessionLocal, get_db

app = FastAPI(title=settings.app_name, version="0.1.0")
PUBLIC_API_PATHS = {
    f"{settings.api_prefix}/health",
    f"{settings.api_prefix}/auth/register",
    f"{settings.api_prefix}/auth/request-otp",
    f"{settings.api_prefix}/auth/verify",
}


@app.middleware("http")
async def require_authenticated_session(request: Request, call_next):
    if (
        request.method == "OPTIONS"
        or not request.url.path.startswith(settings.api_prefix)
        or request.url.path in PUBLIC_API_PATHS
    ):
        return await call_next(request)

    token = request.cookies.get(settings.auth_cookie_name)
    with SessionLocal() as db:
        user = auth.get_user_by_session(db, token)
        if not auth.is_registered(user):
            return JSONResponse(status_code=401, content={"detail": "Oturum açmanız gerekiyor"})
        request.state.user = user
    return await call_next(request)


# CORS is registered after the authentication middleware so even 401 responses
# receive the required browser headers when the UI runs on another local port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_work_order_or_404(
    work_order_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> models.WorkOrder:
    work_order = db.scalar(
        select(models.WorkOrder)
        .join(models.WorkOrder.vehicle)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .where(
            models.WorkOrder.id == work_order_id,
            models.Vehicle.owner_id == user_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="İş emri bulunamadı")
    return work_order


@app.get(f"{settings.api_prefix}/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": settings.app_name}


@app.post(
    f"{settings.api_prefix}/auth/register",
    response_model=schemas.AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: schemas.RegistrationRequest,
    db: Session = Depends(get_db),
) -> schemas.AuthResponse:
    try:
        user = auth.register_user(db, payload)
    except auth.RegistrationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return schemas.AuthResponse(user=schemas.AuthUser.model_validate(user))


@app.post(
    f"{settings.api_prefix}/auth/request-otp",
    response_model=schemas.AuthMessage,
    status_code=status.HTTP_202_ACCEPTED,
)
def request_login_otp(
    payload: schemas.OTPRequest,
    db: Session = Depends(get_db),
) -> schemas.AuthMessage:
    try:
        auth.request_otp(db, str(payload.email), payload.language)
    except auth.UserNotRegisteredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except auth.OTPRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail=f"Yeni kod için {exc.retry_after} saniye bekleyin",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Giriş kodu hazırlanamadı") from exc

    if settings.local_auth_enabled:
        message = "Local login code is ready" if payload.language == "en" else "Yerel giriş kodu hazır"
    else:
        message = (
            "Login code sent to your email"
            if payload.language == "en"
            else "Giriş kodu e-posta adresinize gönderildi"
        )
    return schemas.AuthMessage(
        message=message,
        mailpit_url=None if settings.local_auth_enabled else settings.mailpit_public_url,
        local_code=settings.local_login_code if settings.local_auth_enabled else None,
    )


@app.post(f"{settings.api_prefix}/auth/verify", response_model=schemas.AuthResponse)
def verify_login_otp(
    payload: schemas.OTPVerify,
    response: Response,
    db: Session = Depends(get_db),
) -> schemas.AuthResponse:
    try:
        user, token = auth.verify_otp(db, str(payload.email), payload.code, payload.language)
    except auth.UserNotRegisteredError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except auth.OTPInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.session_expiry_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return schemas.AuthResponse(user=schemas.AuthUser.model_validate(user))


@app.get(f"{settings.api_prefix}/auth/me", response_model=schemas.AuthResponse)
def current_user(request: Request) -> schemas.AuthResponse:
    return schemas.AuthResponse(user=schemas.AuthUser.model_validate(request.state.user))


@app.post(f"{settings.api_prefix}/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    auth.delete_session(
        db,
        request.cookies.get(settings.auth_cookie_name),
        request.state.user.id,
    )
    response.delete_cookie(settings.auth_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.patch(f"{settings.api_prefix}/auth/preferences", response_model=schemas.AuthResponse)
def update_user_preferences(
    payload: schemas.UserPreferencesUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.AuthResponse:
    user = db.get(models.User, request.state.user.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Oturum geçersiz")
    user.preferred_language = payload.preferred_language
    auth.add_audit_event(
        db,
        user.id,
        "account.language_updated",
        entity_type="user",
        entity_id=user.id,
        event_data={"language": payload.preferred_language},
    )
    db.commit()
    db.refresh(user)
    return schemas.AuthResponse(user=schemas.AuthUser.model_validate(user))


@app.patch(f"{settings.api_prefix}/auth/profile", response_model=schemas.AuthResponse)
def update_profile(
    payload: schemas.UserProfileUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.AuthResponse:
    user = db.get(models.User, request.state.user.id)
    if user is None:
        raise HTTPException(status_code=401, detail="Oturum geçersiz")
    try:
        updated = auth.update_profile(db, user, payload)
    except auth.RegistrationConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return schemas.AuthResponse(user=schemas.AuthUser.model_validate(updated))


@app.get(
    f"{settings.api_prefix}/auth/activity",
    response_model=list[schemas.AuditEventRead],
)
def account_activity(
    request: Request,
    db: Session = Depends(get_db),
) -> list[models.AuditEvent]:
    query = (
        select(models.AuditEvent)
        .where(models.AuditEvent.user_id == request.state.user.id)
        .order_by(models.AuditEvent.created_at.desc())
        .limit(50)
    )
    return list(db.scalars(query).all())


@app.post(
    f"{settings.api_prefix}/vehicles",
    response_model=schemas.VehicleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vehicle(
    payload: schemas.VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Vehicle:
    vehicle = models.Vehicle(owner_id=request.state.user.id, **payload.model_dump())
    db.add(vehicle)
    try:
        db.flush()
        auth.add_audit_event(
            db,
            request.state.user.id,
            "vehicle.created",
            entity_type="vehicle",
            entity_id=vehicle.id,
            event_data={"anonymous_code": vehicle.anonymous_code},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Anonim araç kodu zaten kullanılıyor") from exc
    db.refresh(vehicle)
    return vehicle


@app.get(f"{settings.api_prefix}/vehicles", response_model=list[schemas.VehicleRead])
def list_vehicles(request: Request, db: Session = Depends(get_db)) -> list[models.Vehicle]:
    query = (
        select(models.Vehicle)
        .where(models.Vehicle.owner_id == request.state.user.id)
        .order_by(models.Vehicle.created_at.desc())
    )
    return list(db.scalars(query).all())


@app.get(f"{settings.api_prefix}/vehicles/{{vehicle_id}}", response_model=schemas.VehicleRead)
def get_vehicle(
    vehicle_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Vehicle:
    vehicle = db.scalar(
        select(models.Vehicle).where(
            models.Vehicle.id == vehicle_id,
            models.Vehicle.owner_id == request.state.user.id,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")
    return vehicle


@app.patch(f"{settings.api_prefix}/vehicles/{{vehicle_id}}", response_model=schemas.VehicleRead)
def update_vehicle(
    vehicle_id: uuid.UUID,
    payload: schemas.VehicleUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Vehicle:
    vehicle = db.scalar(
        select(models.Vehicle).where(
            models.Vehicle.id == vehicle_id,
            models.Vehicle.owner_id == request.state.user.id,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    auth.add_audit_event(
        db,
        request.state.user.id,
        "vehicle.updated",
        entity_type="vehicle",
        entity_id=vehicle.id,
        event_data={"fields": sorted(payload.model_fields_set)},
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle


@app.post(
    f"{settings.api_prefix}/work-orders",
    response_model=schemas.WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order(
    payload: schemas.WorkOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.WorkOrder:
    vehicle = db.scalar(
        select(models.Vehicle).where(
            models.Vehicle.id == payload.vehicle_id,
            models.Vehicle.owner_id == request.state.user.id,
        )
    )
    if vehicle is None:
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
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "work_order.created",
        entity_type="work_order",
        entity_id=work_order.id,
        event_data={"vehicle_id": str(payload.vehicle_id), "status": payload.status},
    )
    if payload.voice_transcript:
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
def list_work_orders(request: Request, db: Session = Depends(get_db)) -> list[models.WorkOrder]:
    query = (
        select(models.WorkOrder)
        .join(models.WorkOrder.vehicle)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .where(models.Vehicle.owner_id == request.state.user.id)
        .order_by(models.WorkOrder.created_at.desc())
    )
    return list(db.scalars(query).unique().all())


@app.get(f"{settings.api_prefix}/work-orders/{{work_order_id}}", response_model=schemas.WorkOrderRead)
def get_work_order(
    work_order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> models.WorkOrder:
    return get_work_order_or_404(work_order_id, request.state.user.id, db)


@app.patch(f"{settings.api_prefix}/work-orders/{{work_order_id}}", response_model=schemas.WorkOrderRead)
def update_work_order(
    work_order_id: uuid.UUID,
    payload: schemas.WorkOrderUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.WorkOrder:
    work_order = get_work_order_or_404(work_order_id, request.state.user.id, db)
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
    auth.add_audit_event(
        db,
        request.state.user.id,
        "work_order.updated",
        entity_type="work_order",
        entity_id=work_order.id,
        event_data={"fields": sorted(payload.model_fields_set)},
    )
    db.commit()
    return get_work_order_or_404(work_order_id, request.state.user.id, db)


@app.get(f"{settings.api_prefix}/dashboard/summary", response_model=schemas.DashboardSummary)
def dashboard_summary(request: Request, db: Session = Depends(get_db)) -> schemas.DashboardSummary:
    user_id = request.state.user.id
    total_vehicles = (
        db.scalar(
            select(func.count())
            .select_from(models.Vehicle)
            .where(models.Vehicle.owner_id == user_id)
        )
        or 0
    )
    status_rows = db.execute(
        select(models.WorkOrder.status, func.count())
        .join(models.WorkOrder.vehicle)
        .where(models.Vehicle.owner_id == user_id)
        .group_by(models.WorkOrder.status)
    ).all()
    status_counts = {status_name: count for status_name, count in status_rows}
    total_work_orders = sum(status_counts.values())
    completed_work_orders = status_counts.get("completed", 0)
    open_work_orders = total_work_orders - completed_work_orders - status_counts.get("cancelled", 0)
    approved_cases = (
        db.scalar(
            select(func.count())
            .select_from(models.WorkOrder)
            .join(models.WorkOrder.vehicle)
            .where(
                models.Vehicle.owner_id == user_id,
                models.WorkOrder.approved_by_mechanic.is_(True),
            )
        )
        or 0
    )
    recent_query = (
        select(models.WorkOrder)
        .join(models.WorkOrder.vehicle)
        .options(selectinload(models.WorkOrder.dtc_codes))
        .where(models.Vehicle.owner_id == user_id)
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
def search_cases(
    payload: schemas.CaseSearchRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> list[schemas.CaseSearchResult]:
    results = services.search_cases(db, payload, request.state.user.id)
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

