import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from starlette.concurrency import run_in_threadpool

from app import auth, evaluation, finance, inspection, inventory, ml, models, schemas, scheduling, services, test_bank
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


def get_invoice_or_404(
    invoice_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
    *,
    lock_for_update: bool = False,
) -> models.Invoice:
    query = (
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.line_items),
            selectinload(models.Invoice.payments),
        )
        .where(
            models.Invoice.id == invoice_id,
            models.Invoice.owner_id == user_id,
        )
    )
    if lock_for_update:
        query = query.with_for_update()
    invoice = db.scalar(query)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı")
    return invoice


def get_inventory_part_or_404(
    part_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
    *,
    lock_for_update: bool = False,
) -> models.InventoryPart:
    query = select(models.InventoryPart).where(
        models.InventoryPart.id == part_id,
        models.InventoryPart.owner_id == user_id,
    )
    if lock_for_update:
        query = query.with_for_update()
    part = db.scalar(query)
    if part is None:
        raise HTTPException(status_code=404, detail="Stok parçası bulunamadı")
    return part


def get_appointment_or_404(
    appointment_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> models.Appointment:
    appointment = db.scalar(
        select(models.Appointment).where(
            models.Appointment.id == appointment_id,
            models.Appointment.owner_id == user_id,
        )
    )
    if appointment is None:
        raise HTTPException(status_code=404, detail="Randevu bulunamadı")
    return appointment


def get_reminder_or_404(
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> models.MaintenanceReminder:
    reminder = db.scalar(
        select(models.MaintenanceReminder)
        .options(selectinload(models.MaintenanceReminder.vehicle))
        .where(
            models.MaintenanceReminder.id == reminder_id,
            models.MaintenanceReminder.owner_id == user_id,
        )
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Bakım hatırlatması bulunamadı")
    return reminder


def ensure_owned_vehicle(vehicle_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> models.Vehicle:
    vehicle = db.scalar(
        select(models.Vehicle).where(
            models.Vehicle.id == vehicle_id,
            models.Vehicle.owner_id == user_id,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Araç bulunamadı")
    return vehicle


def ensure_technician_available(
    *,
    user_id: uuid.UUID,
    technician: str | None,
    scheduled_start: datetime,
    scheduled_end: datetime,
    appointment_status: str,
    db: Session,
    exclude_id: uuid.UUID | None = None,
) -> None:
    if not technician or appointment_status in {"completed", "cancelled", "no_show"}:
        return
    query = select(models.Appointment.id).where(
        models.Appointment.owner_id == user_id,
        func.lower(models.Appointment.assigned_technician) == technician.strip().lower(),
        models.Appointment.status.notin_(["completed", "cancelled", "no_show"]),
        models.Appointment.scheduled_start < scheduled_end,
        models.Appointment.scheduled_end > scheduled_start,
    )
    if exclude_id is not None:
        query = query.where(models.Appointment.id != exclude_id)
    if db.scalar(query) is not None:
        raise HTTPException(
            status_code=409,
            detail="Bu usta için seçilen saat aralığında başka bir randevu var",
        )


def reminder_read(reminder: models.MaintenanceReminder) -> schemas.MaintenanceReminderRead:
    return schemas.MaintenanceReminderRead(
        id=reminder.id,
        vehicle_id=reminder.vehicle_id,
        title=reminder.title,
        due_date=reminder.due_date,
        due_mileage=reminder.due_mileage,
        status=reminder.status,
        due_state=scheduling.reminder_state(
            status=reminder.status,
            due_date=reminder.due_date,
            due_mileage=reminder.due_mileage,
            current_mileage=reminder.vehicle.mileage,
        ),
        notes=reminder.notes,
        completed_at=reminder.completed_at,
        created_at=reminder.created_at,
        updated_at=reminder.updated_at,
    )


def get_inspection_or_404(
    inspection_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session,
) -> models.InspectionReport:
    report = db.scalar(
        select(models.InspectionReport)
        .options(
            selectinload(models.InspectionReport.items),
            selectinload(models.InspectionReport.work_order).selectinload(models.WorkOrder.vehicle),
        )
        .where(
            models.InspectionReport.id == inspection_id,
            models.InspectionReport.owner_id == user_id,
        )
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Araç kontrol formu bulunamadı")
    return report


def inspection_read(report: models.InspectionReport) -> schemas.InspectionReportRead:
    summary = inspection.summarize(report.items)
    return schemas.InspectionReportRead(
        id=report.id,
        work_order_id=report.work_order_id,
        status=report.status,
        odometer=report.odometer,
        technician_name=report.technician_name,
        notes=report.notes,
        mechanic_approved=report.mechanic_approved,
        completed_at=report.completed_at,
        created_at=report.created_at,
        updated_at=report.updated_at,
        items=[schemas.InspectionItemRead.model_validate(item) for item in report.items],
        **summary,
    )


def get_card_challenge_or_404(
    challenge_id: uuid.UUID,
    token: str,
    user_id: uuid.UUID,
    db: Session,
    *,
    lock_for_update: bool = False,
) -> models.CardPaymentChallenge:
    query = (
        select(models.CardPaymentChallenge)
        .options(selectinload(models.CardPaymentChallenge.invoice))
        .where(
            models.CardPaymentChallenge.id == challenge_id,
            models.CardPaymentChallenge.owner_id == user_id,
        )
    )
    if lock_for_update:
        query = query.with_for_update()
    challenge = db.scalar(query)
    if challenge is None or not test_bank.token_matches(token, challenge.token_hash):
        raise HTTPException(status_code=404, detail="3D Secure işlemi bulunamadı")
    return challenge


def evaluation_run_to_read(run: models.EvaluationRun) -> schemas.EvaluationRunRead:
    return schemas.EvaluationRunRead(
        id=run.id,
        modes=run.modes,
        top_k=run.top_k,
        query_count=run.query_count,
        metrics=[schemas.EvaluationModeMetrics.model_validate(item) for item in run.metrics_json],
        details=[schemas.EvaluationDetail.model_validate(item) for item in run.details_json],
        best_mode=run.best_mode,
        created_at=run.created_at,
    )


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


@app.post(
    f"{settings.api_prefix}/inventory/parts",
    response_model=schemas.InventoryPartRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inventory_part(
    payload: schemas.InventoryPartCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.InventoryPart:
    data = payload.model_dump(exclude={"initial_quantity"})
    part = models.InventoryPart(
        owner_id=request.state.user.id,
        stock_quantity=inventory.quantity(payload.initial_quantity),
        **data,
    )
    db.add(part)
    try:
        db.flush()
        if part.stock_quantity > Decimal("0"):
            db.add(
                models.StockMovement(
                    part_id=part.id,
                    created_by_id=request.state.user.id,
                    movement_type="initial",
                    quantity_delta=part.stock_quantity,
                    balance_after=part.stock_quantity,
                    notes="İlk stok",
                )
            )
        auth.add_audit_event(
            db,
            request.state.user.id,
            "inventory.part_created",
            entity_type="inventory_part",
            entity_id=part.id,
            event_data={"sku": part.sku, "initial_quantity": str(part.stock_quantity)},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu stok kodu zaten kullanılıyor") from exc
    db.refresh(part)
    return part


@app.get(
    f"{settings.api_prefix}/inventory/parts",
    response_model=list[schemas.InventoryPartRead],
)
def list_inventory_parts(
    request: Request,
    db: Session = Depends(get_db),
) -> list[models.InventoryPart]:
    query = (
        select(models.InventoryPart)
        .where(models.InventoryPart.owner_id == request.state.user.id)
        .order_by(models.InventoryPart.active.desc(), models.InventoryPart.name)
    )
    return list(db.scalars(query).all())


@app.patch(
    f"{settings.api_prefix}/inventory/parts/{{part_id}}",
    response_model=schemas.InventoryPartRead,
)
def update_inventory_part(
    part_id: uuid.UUID,
    payload: schemas.InventoryPartUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.InventoryPart:
    part = get_inventory_part_or_404(part_id, request.state.user.id, db)
    update_data = payload.model_dump(exclude_unset=True)
    required_fields = {
        "sku", "name", "unit", "low_stock_threshold", "purchase_price", "sale_price", "active"
    }
    if any(field in update_data and update_data[field] is None for field in required_fields):
        raise HTTPException(status_code=422, detail="Zorunlu parça alanları boş bırakılamaz")
    for field, value in update_data.items():
        setattr(part, field, value)
    try:
        auth.add_audit_event(
            db,
            request.state.user.id,
            "inventory.part_updated",
            entity_type="inventory_part",
            entity_id=part.id,
            event_data={"fields": sorted(payload.model_fields_set)},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu stok kodu zaten kullanılıyor") from exc
    db.refresh(part)
    return part


@app.post(
    f"{settings.api_prefix}/inventory/parts/{{part_id}}/movements",
    response_model=schemas.InventoryPartRead,
    status_code=status.HTTP_201_CREATED,
)
def record_stock_movement(
    part_id: uuid.UUID,
    payload: schemas.StockMovementCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.InventoryPart:
    part = get_inventory_part_or_404(
        part_id,
        request.state.user.id,
        db,
        lock_for_update=True,
    )
    try:
        delta, balance = inventory.apply_movement(
            part.stock_quantity,
            payload.movement_type,
            payload.quantity,
        )
    except inventory.InsufficientStockError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Yetersiz stok. Mevcut miktar: {part.stock_quantity} {part.unit}",
        ) from exc
    part.stock_quantity = balance
    movement = models.StockMovement(
        part_id=part.id,
        created_by_id=request.state.user.id,
        movement_type=payload.movement_type,
        quantity_delta=delta,
        balance_after=balance,
        reference_type="manual",
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(movement)
    auth.add_audit_event(
        db,
        request.state.user.id,
        "inventory.stock_moved",
        entity_type="inventory_part",
        entity_id=part.id,
        event_data={
            "movement_type": payload.movement_type,
            "quantity_delta": str(delta),
            "balance_after": str(balance),
        },
    )
    db.commit()
    db.refresh(part)
    return part


@app.get(
    f"{settings.api_prefix}/inventory/movements",
    response_model=list[schemas.StockMovementRead],
)
def list_stock_movements(
    request: Request,
    part_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[models.StockMovement]:
    query = (
        select(models.StockMovement)
        .join(models.StockMovement.part)
        .where(models.InventoryPart.owner_id == request.state.user.id)
        .order_by(models.StockMovement.created_at.desc())
        .limit(100)
    )
    if part_id is not None:
        query = query.where(models.StockMovement.part_id == part_id)
    return list(db.scalars(query).all())


@app.get(
    f"{settings.api_prefix}/inventory/summary",
    response_model=schemas.InventorySummary,
)
def inventory_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InventorySummary:
    parts = list(
        db.scalars(
            select(models.InventoryPart).where(
                models.InventoryPart.owner_id == request.state.user.id,
                models.InventoryPart.active.is_(True),
            )
        ).all()
    )
    cost_value, sale_value = inventory.inventory_values(parts)
    return schemas.InventorySummary(
        total_parts=len(parts),
        low_stock_parts=sum(part.is_low_stock for part in parts),
        out_of_stock_parts=sum(part.stock_quantity == Decimal("0") for part in parts),
        inventory_cost_value=cost_value,
        inventory_sale_value=sale_value,
    )


@app.post(
    f"{settings.api_prefix}/work-orders/{{work_order_id}}/invoice",
    response_model=schemas.InvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_invoice(
    work_order_id: uuid.UUID,
    payload: schemas.InvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InvoiceRead:
    work_order = get_work_order_or_404(work_order_id, request.state.user.id, db)
    if db.scalar(select(models.Invoice.id).where(models.Invoice.work_order_id == work_order.id)):
        raise HTTPException(status_code=409, detail="Bu iş emri için zaten fatura oluşturulmuş")

    part_requirements: dict[uuid.UUID, Decimal] = {}
    for item in payload.line_items:
        if item.inventory_part_id is None:
            continue
        if item.item_type != "part":
            raise HTTPException(
                status_code=422,
                detail="Stok parçası yalnızca parça türündeki fatura kalemine bağlanabilir",
            )
        part_requirements[item.inventory_part_id] = (
            part_requirements.get(item.inventory_part_id, Decimal("0")) + item.quantity
        )

    stock_parts: dict[uuid.UUID, models.InventoryPart] = {}
    stock_updates: dict[uuid.UUID, tuple[Decimal, Decimal]] = {}
    if part_requirements:
        locked_parts = list(
            db.scalars(
                select(models.InventoryPart)
                .where(
                    models.InventoryPart.owner_id == request.state.user.id,
                    models.InventoryPart.active.is_(True),
                    models.InventoryPart.id.in_(part_requirements),
                )
                .with_for_update()
            ).all()
        )
        stock_parts = {part.id: part for part in locked_parts}
        if len(stock_parts) != len(part_requirements):
            raise HTTPException(status_code=404, detail="Faturadaki stok parçalarından biri bulunamadı")
        for part_id, required in part_requirements.items():
            part = stock_parts[part_id]
            try:
                stock_updates[part_id] = inventory.apply_movement(
                    part.stock_quantity,
                    "invoice_sale",
                    required,
                )
            except inventory.InsufficientStockError as exc:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"{part.name} için stok yetersiz. "
                        f"Gerekli: {required}, mevcut: {part.stock_quantity} {part.unit}"
                    ),
                ) from exc

    try:
        line_totals, subtotal, tax_amount, total_amount = finance.calculate_invoice(
            payload.line_items,
            payload.discount_amount,
            payload.tax_rate,
        )
    except finance.FinanceValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    invoice_id = uuid.uuid4()
    invoice = models.Invoice(
        id=invoice_id,
        owner_id=request.state.user.id,
        work_order_id=work_order.id,
        invoice_number=f"FTR-{datetime.now(timezone.utc).year}-{invoice_id.hex[:8].upper()}",
        subtotal=subtotal,
        discount_amount=finance.money(payload.discount_amount),
        tax_rate=payload.tax_rate,
        tax_amount=tax_amount,
        total_amount=total_amount,
        notes=payload.notes,
        due_date=payload.due_date,
        line_items=[
            models.InvoiceLineItem(
                item_type=item.item_type,
                inventory_part_id=item.inventory_part_id,
                description=item.description.strip(),
                quantity=item.quantity,
                unit_price=item.unit_price,
                line_total=line_totals[index],
            )
            for index, item in enumerate(payload.line_items)
        ],
    )
    db.add(invoice)
    for part_id, (delta, balance) in stock_updates.items():
        part = stock_parts[part_id]
        part.stock_quantity = balance
        db.add(
            models.StockMovement(
                part_id=part.id,
                created_by_id=request.state.user.id,
                movement_type="invoice_sale",
                quantity_delta=delta,
                balance_after=balance,
                reference_type="invoice",
                reference_id=invoice.id,
                notes=invoice.invoice_number,
            )
        )
    try:
        db.flush()
        auth.add_audit_event(
            db,
            request.state.user.id,
            "invoice.created",
            entity_type="invoice",
            entity_id=invoice.id,
            event_data={
                "invoice_number": invoice.invoice_number,
                "total": str(total_amount),
                "stock_part_count": len(stock_updates),
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bu iş emri için zaten fatura oluşturulmuş") from exc
    return finance.to_read(get_invoice_or_404(invoice.id, request.state.user.id, db))


@app.get(f"{settings.api_prefix}/invoices", response_model=list[schemas.InvoiceRead])
def list_invoices(request: Request, db: Session = Depends(get_db)) -> list[schemas.InvoiceRead]:
    query = (
        select(models.Invoice)
        .options(
            selectinload(models.Invoice.line_items),
            selectinload(models.Invoice.payments),
        )
        .where(models.Invoice.owner_id == request.state.user.id)
        .order_by(models.Invoice.created_at.desc())
    )
    return [finance.to_read(invoice) for invoice in db.scalars(query).unique().all()]


@app.get(f"{settings.api_prefix}/invoices/{{invoice_id}}", response_model=schemas.InvoiceRead)
def get_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InvoiceRead:
    return finance.to_read(get_invoice_or_404(invoice_id, request.state.user.id, db))


@app.post(
    f"{settings.api_prefix}/invoices/{{invoice_id}}/payments",
    response_model=schemas.InvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
def record_payment(
    invoice_id: uuid.UUID,
    payload: schemas.PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InvoiceRead:
    invoice = get_invoice_or_404(
        invoice_id,
        request.state.user.id,
        db,
        lock_for_update=True,
    )
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="İptal edilmiş faturaya ödeme eklenemez")
    remaining = finance.balance_due(invoice)
    amount = finance.money(payload.amount)
    if amount > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Ödeme kalan {remaining} TRY tutarını aşamaz",
        )

    payment = models.Payment(
        invoice_id=invoice.id,
        created_by_id=request.state.user.id,
        amount=amount,
        method=payload.method,
        reference=payload.reference.strip() if payload.reference else None,
        notes=payload.notes.strip() if payload.notes else None,
    )
    invoice.payments.append(payment)
    finance.update_status(invoice)
    db.add(payment)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "payment.recorded",
        entity_type="payment",
        entity_id=payment.id,
        event_data={
            "invoice_number": invoice.invoice_number,
            "amount": str(amount),
            "method": payload.method,
        },
    )
    db.commit()
    return finance.to_read(get_invoice_or_404(invoice.id, request.state.user.id, db))


@app.post(
    f"{settings.api_prefix}/invoices/{{invoice_id}}/card-payment/start",
    response_model=schemas.CardPaymentStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_test_card_payment(
    invoice_id: uuid.UUID,
    payload: schemas.CardPaymentStart,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.CardPaymentStartResponse:
    invoice = get_invoice_or_404(
        invoice_id,
        request.state.user.id,
        db,
        lock_for_update=True,
    )
    if invoice.status == "cancelled":
        raise HTTPException(status_code=409, detail="İptal edilmiş fatura ödenemez")
    amount = finance.money(payload.amount)
    remaining = finance.balance_due(invoice)
    if amount > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Kart ödemesi kalan {remaining} TRY tutarını aşamaz",
        )

    raw_token, hashed_token = test_bank.create_token()
    challenge = models.CardPaymentChallenge(
        owner_id=request.state.user.id,
        invoice_id=invoice.id,
        token_hash=hashed_token,
        amount=amount,
        card_last4=payload.card_last4,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.test_3d_expiry_minutes),
    )
    db.add(challenge)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "card_payment.challenge_started",
        entity_type="card_payment_challenge",
        entity_id=challenge.id,
        event_data={
            "invoice_number": invoice.invoice_number,
            "amount": str(amount),
            "card_last4": payload.card_last4,
        },
    )
    db.commit()
    db.refresh(challenge)
    return schemas.CardPaymentStartResponse(
        challenge_id=challenge.id,
        redirect_url=(
            f"/test-bank/3d?challenge_id={challenge.id}#token={raw_token}"
        ),
        expires_at=challenge.expires_at,
    )


@app.post(
    f"{settings.api_prefix}/card-payment/challenges/{{challenge_id}}/details",
    response_model=schemas.CardChallengeRead,
)
def test_card_challenge_details(
    challenge_id: uuid.UUID,
    payload: schemas.CardChallengeAccess,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.CardChallengeRead:
    challenge = get_card_challenge_or_404(
        challenge_id,
        payload.token,
        request.state.user.id,
        db,
    )
    if challenge.status == "pending" and test_bank.is_expired(challenge.expires_at):
        challenge.status = "expired"
        db.commit()
    return schemas.CardChallengeRead(
        challenge_id=challenge.id,
        invoice_id=challenge.invoice_id,
        invoice_number=challenge.invoice.invoice_number,
        amount=challenge.amount,
        currency=challenge.invoice.currency,
        card_last4=challenge.card_last4,
        status=challenge.status,
        expires_at=challenge.expires_at,
        attempts_remaining=max(settings.test_3d_max_attempts - challenge.attempts, 0),
    )


@app.post(
    f"{settings.api_prefix}/card-payment/challenges/{{challenge_id}}/verify",
    response_model=schemas.CardChallengeVerifyResponse,
)
def verify_test_card_challenge(
    challenge_id: uuid.UUID,
    payload: schemas.CardChallengeVerify,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.CardChallengeVerifyResponse:
    challenge = get_card_challenge_or_404(
        challenge_id,
        payload.token,
        request.state.user.id,
        db,
        lock_for_update=True,
    )
    attempts_remaining = max(settings.test_3d_max_attempts - challenge.attempts, 0)
    if challenge.status == "succeeded":
        return schemas.CardChallengeVerifyResponse(
            status="succeeded",
            message="Ödeme daha önce başarıyla tamamlandı",
            attempts_remaining=attempts_remaining,
            redirect_url=f"/finance?payment=success&invoice={challenge.invoice_id}",
        )
    if challenge.status in {"failed", "expired"}:
        return schemas.CardChallengeVerifyResponse(
            status=challenge.status,
            message=(
                "3D Secure işleminin süresi doldu"
                if challenge.status == "expired"
                else "3D Secure işlemi başarısız oldu"
            ),
            attempts_remaining=attempts_remaining,
        )
    if test_bank.is_expired(challenge.expires_at):
        challenge.status = "expired"
        db.commit()
        return schemas.CardChallengeVerifyResponse(
            status="expired",
            message="3D Secure işleminin süresi doldu",
            attempts_remaining=0,
        )

    if payload.code != settings.test_3d_secure_code:
        challenge.attempts += 1
        attempts_remaining = max(settings.test_3d_max_attempts - challenge.attempts, 0)
        if attempts_remaining == 0:
            challenge.status = "failed"
            auth.add_audit_event(
                db,
                request.state.user.id,
                "card_payment.challenge_failed",
                entity_type="card_payment_challenge",
                entity_id=challenge.id,
                event_data={"invoice_number": challenge.invoice.invoice_number},
            )
        db.commit()
        return schemas.CardChallengeVerifyResponse(
            status=challenge.status,
            message=(
                "Doğrulama kodu hatalı; işlem başarısız oldu"
                if challenge.status == "failed"
                else "Doğrulama kodu hatalı"
            ),
            attempts_remaining=attempts_remaining,
        )

    invoice = get_invoice_or_404(
        challenge.invoice_id,
        request.state.user.id,
        db,
        lock_for_update=True,
    )
    remaining = finance.balance_due(invoice)
    if challenge.amount > remaining:
        challenge.status = "failed"
        db.commit()
        return schemas.CardChallengeVerifyResponse(
            status="failed",
            message="Fatura bakiyesi değiştiği için ödeme tamamlanamadı",
            attempts_remaining=attempts_remaining,
        )

    payment = models.Payment(
        invoice_id=invoice.id,
        created_by_id=request.state.user.id,
        amount=challenge.amount,
        method="test_card",
        reference=f"3DS-{challenge.id.hex[:10].upper()}",
        notes="Yerel test bankası 3D Secure simülasyonu",
    )
    invoice.payments.append(payment)
    finance.update_status(invoice)
    challenge.status = "succeeded"
    challenge.completed_at = datetime.now(timezone.utc)
    db.add(payment)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "card_payment.succeeded",
        entity_type="payment",
        entity_id=payment.id,
        event_data={
            "invoice_number": invoice.invoice_number,
            "amount": str(challenge.amount),
            "method": "test_card",
            "card_last4": challenge.card_last4,
        },
    )
    db.commit()
    return schemas.CardChallengeVerifyResponse(
        status="succeeded",
        message="Test kart ödemesi başarıyla tamamlandı",
        attempts_remaining=attempts_remaining,
        redirect_url=f"/finance?payment=success&invoice={invoice.id}",
    )


@app.get(f"{settings.api_prefix}/finance/summary", response_model=schemas.FinanceSummary)
def finance_summary(request: Request, db: Session = Depends(get_db)) -> schemas.FinanceSummary:
    invoices = list(
        db.scalars(
            select(models.Invoice)
            .options(selectinload(models.Invoice.payments))
            .where(models.Invoice.owner_id == request.state.user.id)
        ).unique().all()
    )
    active_invoices = [invoice for invoice in invoices if invoice.status != "cancelled"]
    invoiced_total = finance.money(
        sum((invoice.total_amount for invoice in active_invoices), Decimal("0"))
    )
    collected_total = finance.money(
        sum((finance.paid_amount(invoice) for invoice in active_invoices), Decimal("0"))
    )
    today = date.today()
    return schemas.FinanceSummary(
        invoiced_total=invoiced_total,
        collected_total=collected_total,
        outstanding_total=finance.money(invoiced_total - collected_total),
        total_invoices=len(active_invoices),
        paid_invoices=sum(invoice.status == "paid" for invoice in active_invoices),
        partially_paid_invoices=sum(
            invoice.status == "partially_paid" for invoice in active_invoices
        ),
        overdue_invoices=sum(
            invoice.due_date is not None
            and invoice.due_date < today
            and finance.balance_due(invoice) > Decimal("0")
            for invoice in active_invoices
        ),
    )


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


@app.post(
    f"{settings.api_prefix}/evaluation/queries",
    response_model=schemas.EvaluationQueryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_query(
    payload: schemas.EvaluationQueryCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.EvaluationQuery:
    expected_order = get_work_order_or_404(
        payload.expected_work_order_id,
        request.state.user.id,
        db,
    )
    if not expected_order.approved_by_mechanic:
        raise HTTPException(
            status_code=409,
            detail="Değerlendirme hedefi usta tarafından onaylanmış bir vaka olmalıdır",
        )
    evaluation_query = models.EvaluationQuery(
        owner_id=request.state.user.id,
        **payload.model_dump(),
    )
    db.add(evaluation_query)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "evaluation.query_created",
        entity_type="evaluation_query",
        entity_id=evaluation_query.id,
        event_data={"expected_work_order_id": str(payload.expected_work_order_id)},
    )
    db.commit()
    db.refresh(evaluation_query)
    return evaluation_query


@app.get(
    f"{settings.api_prefix}/evaluation/queries",
    response_model=list[schemas.EvaluationQueryRead],
)
def list_evaluation_queries(
    request: Request,
    db: Session = Depends(get_db),
) -> list[models.EvaluationQuery]:
    return list(
        db.scalars(
            select(models.EvaluationQuery)
            .where(models.EvaluationQuery.owner_id == request.state.user.id)
            .order_by(models.EvaluationQuery.created_at.desc())
        ).all()
    )


@app.delete(
    f"{settings.api_prefix}/evaluation/queries/{{query_id}}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evaluation_query(
    query_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    evaluation_query = db.scalar(
        select(models.EvaluationQuery).where(
            models.EvaluationQuery.id == query_id,
            models.EvaluationQuery.owner_id == request.state.user.id,
        )
    )
    if evaluation_query is None:
        raise HTTPException(status_code=404, detail="Değerlendirme sorgusu bulunamadı")
    db.delete(evaluation_query)
    auth.add_audit_event(
        db,
        request.state.user.id,
        "evaluation.query_deleted",
        entity_type="evaluation_query",
        entity_id=evaluation_query.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    f"{settings.api_prefix}/evaluation/runs",
    response_model=schemas.EvaluationRunRead,
    status_code=status.HTTP_201_CREATED,
)
def run_evaluation(
    payload: schemas.EvaluationRunRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.EvaluationRunRead:
    queries = list(
        db.scalars(
            select(models.EvaluationQuery)
            .where(models.EvaluationQuery.owner_id == request.state.user.id)
            .order_by(models.EvaluationQuery.created_at)
            .limit(200)
        ).all()
    )
    if not queries:
        raise HTTPException(
            status_code=409,
            detail="Deney çalıştırmadan önce en az bir değerlendirme sorgusu ekleyin",
        )
    metrics, details, best_mode = evaluation.run_retrieval_evaluation(
        db,
        queries,
        payload.modes,
        payload.top_k,
        request.state.user.id,
    )
    run = models.EvaluationRun(
        owner_id=request.state.user.id,
        modes=payload.modes,
        top_k=payload.top_k,
        query_count=len(queries),
        metrics_json=metrics,
        details_json=details,
        best_mode=best_mode,
    )
    db.add(run)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "evaluation.run_completed",
        entity_type="evaluation_run",
        entity_id=run.id,
        event_data={
            "modes": payload.modes,
            "top_k": payload.top_k,
            "query_count": len(queries),
            "best_mode": best_mode,
        },
    )
    db.commit()
    db.refresh(run)
    return evaluation_run_to_read(run)


@app.get(
    f"{settings.api_prefix}/evaluation/runs",
    response_model=list[schemas.EvaluationRunRead],
)
def list_evaluation_runs(
    request: Request,
    db: Session = Depends(get_db),
) -> list[schemas.EvaluationRunRead]:
    runs = db.scalars(
        select(models.EvaluationRun)
        .where(models.EvaluationRun.owner_id == request.state.user.id)
        .order_by(models.EvaluationRun.created_at.desc())
        .limit(30)
    ).all()
    return [evaluation_run_to_read(run) for run in runs]


@app.get(
    f"{settings.api_prefix}/evaluation/summary",
    response_model=schemas.EvaluationSummary,
)
def evaluation_summary(
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.EvaluationSummary:
    query_count = db.scalar(
        select(func.count())
        .select_from(models.EvaluationQuery)
        .where(models.EvaluationQuery.owner_id == request.state.user.id)
    ) or 0
    runs = list(
        db.scalars(
            select(models.EvaluationRun)
            .where(models.EvaluationRun.owner_id == request.state.user.id)
            .order_by(models.EvaluationRun.created_at.desc())
        ).all()
    )
    best_metric: dict | None = None
    for run in runs:
        for metric in run.metrics_json:
            if best_metric is None or (
                metric["hit_rate"], metric["mrr"], -metric["avg_latency_ms"]
            ) > (
                best_metric["hit_rate"],
                best_metric["mrr"],
                -best_metric["avg_latency_ms"],
            ):
                best_metric = metric
    return schemas.EvaluationSummary(
        query_count=query_count,
        run_count=len(runs),
        best_mode=best_metric["mode"] if best_metric else None,
        best_hit_rate=best_metric["hit_rate"] if best_metric else 0,
        latest_run_at=runs[0].created_at if runs else None,
    )


@app.post(
    f"{settings.api_prefix}/cases/evidence",
    response_model=schemas.EvidenceResponse,
)
def evidence_based_assistance(
    payload: schemas.EvidenceRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.EvidenceResponse:
    search_payload = schemas.CaseSearchRequest(
        query=payload.query,
        dtc_code=payload.dtc_code,
        limit=5,
        search_mode=payload.search_mode,
        approved_only=True,
    )
    matches = services.search_cases(db, search_payload, request.state.user.id)
    synthesis = evaluation.build_evidence_summary(matches)
    evidence_items = [
        schemas.CaseSearchResult(
            work_order=schemas.WorkOrderRead.model_validate(match.work_order),
            vehicle=schemas.VehicleRead.model_validate(match.work_order.vehicle),
            match_reason=match.reason,
            similarity_score=round(match.score, 4),
            search_method=match.method,
        )
        for match in matches
    ]
    return schemas.EvidenceResponse(**synthesis, evidence=evidence_items)


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


@app.post(
    f"{settings.api_prefix}/appointments",
    response_model=schemas.AppointmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    payload: schemas.AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Appointment:
    ensure_owned_vehicle(payload.vehicle_id, request.state.user.id, db)
    try:
        scheduled_start, scheduled_end = scheduling.normalize_interval(
            payload.scheduled_start, payload.scheduled_end
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    technician = payload.assigned_technician.strip() if payload.assigned_technician else None
    ensure_technician_available(
        user_id=request.state.user.id,
        technician=technician,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        appointment_status=payload.status,
        db=db,
    )
    appointment = models.Appointment(
        **payload.model_dump(exclude={"scheduled_start", "scheduled_end", "assigned_technician"}),
        owner_id=request.state.user.id,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        assigned_technician=technician,
    )
    db.add(appointment)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "appointment.created",
        entity_type="appointment",
        entity_id=appointment.id,
        event_data={
            "vehicle_id": str(appointment.vehicle_id),
            "status": appointment.status,
            "scheduled_start": appointment.scheduled_start.isoformat(),
        },
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@app.get(f"{settings.api_prefix}/appointments", response_model=list[schemas.AppointmentRead])
def list_appointments(request: Request, db: Session = Depends(get_db)) -> list[models.Appointment]:
    return list(
        db.scalars(
            select(models.Appointment)
            .where(models.Appointment.owner_id == request.state.user.id)
            .order_by(models.Appointment.scheduled_start.asc())
        ).all()
    )


@app.patch(
    f"{settings.api_prefix}/appointments/{{appointment_id}}",
    response_model=schemas.AppointmentRead,
)
def update_appointment(
    appointment_id: uuid.UUID,
    payload: schemas.AppointmentUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> models.Appointment:
    appointment = get_appointment_or_404(appointment_id, request.state.user.id, db)
    changes = payload.model_dump(exclude_unset=True)
    required_fields = {
        "vehicle_id", "scheduled_start", "scheduled_end", "service_type", "customer_complaint", "status"
    }
    if any(field in changes and changes[field] is None for field in required_fields):
        raise HTTPException(status_code=422, detail="Zorunlu randevu alanları boş bırakılamaz")
    vehicle_id = changes.get("vehicle_id", appointment.vehicle_id)
    if "vehicle_id" in changes:
        ensure_owned_vehicle(vehicle_id, request.state.user.id, db)
    raw_start = changes.get("scheduled_start", appointment.scheduled_start)
    raw_end = changes.get("scheduled_end", appointment.scheduled_end)
    try:
        scheduled_start, scheduled_end = scheduling.normalize_interval(raw_start, raw_end)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    technician_value = changes.get("assigned_technician", appointment.assigned_technician)
    technician = technician_value.strip() if technician_value else None
    appointment_status = changes.get("status", appointment.status)
    ensure_technician_available(
        user_id=request.state.user.id,
        technician=technician,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        appointment_status=appointment_status,
        db=db,
        exclude_id=appointment.id,
    )
    changes["scheduled_start"] = scheduled_start
    changes["scheduled_end"] = scheduled_end
    changes["assigned_technician"] = technician
    for field, value in changes.items():
        setattr(appointment, field, value)
    auth.add_audit_event(
        db,
        request.state.user.id,
        "appointment.updated",
        entity_type="appointment",
        entity_id=appointment.id,
        event_data={"fields": sorted(payload.model_fields_set), "status": appointment.status},
    )
    db.commit()
    db.refresh(appointment)
    return appointment


@app.post(
    f"{settings.api_prefix}/maintenance-reminders",
    response_model=schemas.MaintenanceReminderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_reminder(
    payload: schemas.MaintenanceReminderCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.MaintenanceReminderRead:
    vehicle = ensure_owned_vehicle(payload.vehicle_id, request.state.user.id, db)
    reminder = models.MaintenanceReminder(
        **payload.model_dump(),
        owner_id=request.state.user.id,
        vehicle=vehicle,
    )
    db.add(reminder)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "maintenance_reminder.created",
        entity_type="maintenance_reminder",
        entity_id=reminder.id,
        event_data={"vehicle_id": str(reminder.vehicle_id), "title": reminder.title},
    )
    db.commit()
    db.refresh(reminder)
    return reminder_read(reminder)


@app.get(
    f"{settings.api_prefix}/maintenance-reminders",
    response_model=list[schemas.MaintenanceReminderRead],
)
def list_maintenance_reminders(
    request: Request,
    db: Session = Depends(get_db),
) -> list[schemas.MaintenanceReminderRead]:
    reminders = list(
        db.scalars(
            select(models.MaintenanceReminder)
            .options(selectinload(models.MaintenanceReminder.vehicle))
            .where(models.MaintenanceReminder.owner_id == request.state.user.id)
            .order_by(models.MaintenanceReminder.created_at.desc())
        ).all()
    )
    return [reminder_read(reminder) for reminder in reminders]


@app.patch(
    f"{settings.api_prefix}/maintenance-reminders/{{reminder_id}}",
    response_model=schemas.MaintenanceReminderRead,
)
def update_maintenance_reminder(
    reminder_id: uuid.UUID,
    payload: schemas.MaintenanceReminderUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.MaintenanceReminderRead:
    reminder = get_reminder_or_404(reminder_id, request.state.user.id, db)
    changes = payload.model_dump(exclude_unset=True)
    required_fields = {"vehicle_id", "title", "status"}
    if any(field in changes and changes[field] is None for field in required_fields):
        raise HTTPException(status_code=422, detail="Zorunlu bakım alanları boş bırakılamaz")
    vehicle_id = changes.get("vehicle_id", reminder.vehicle_id)
    if "vehicle_id" in changes:
        reminder.vehicle = ensure_owned_vehicle(vehicle_id, request.state.user.id, db)
    due_date = changes.get("due_date", reminder.due_date)
    due_mileage = changes.get("due_mileage", reminder.due_mileage)
    if due_date is None and due_mileage is None:
        raise HTTPException(
            status_code=422,
            detail="Bakım hatırlatması için tarih veya kilometre girilmelidir",
        )
    for field, value in changes.items():
        if field != "vehicle_id":
            setattr(reminder, field, value)
    if "status" in changes:
        reminder.completed_at = (
            datetime.now(timezone.utc) if changes["status"] == "completed" else None
        )
    auth.add_audit_event(
        db,
        request.state.user.id,
        "maintenance_reminder.updated",
        entity_type="maintenance_reminder",
        entity_id=reminder.id,
        event_data={"fields": sorted(payload.model_fields_set), "status": reminder.status},
    )
    db.commit()
    db.refresh(reminder)
    return reminder_read(reminder)


@app.get(f"{settings.api_prefix}/schedule/summary", response_model=schemas.ScheduleSummary)
def schedule_summary(request: Request, db: Session = Depends(get_db)) -> schemas.ScheduleSummary:
    user_id = request.state.user.id
    today = scheduling.workshop_today()
    day_start, day_end = scheduling.local_day_bounds(today)
    now = datetime.now(timezone.utc)
    upcoming_end = now + timedelta(days=7)
    active_statuses = ["scheduled", "confirmed", "checked_in", "in_service"]
    today_count = db.scalar(
        select(func.count()).select_from(models.Appointment).where(
            models.Appointment.owner_id == user_id,
            models.Appointment.scheduled_start >= day_start,
            models.Appointment.scheduled_start < day_end,
            models.Appointment.status.notin_(["cancelled", "no_show"]),
        )
    ) or 0
    upcoming_count = db.scalar(
        select(func.count()).select_from(models.Appointment).where(
            models.Appointment.owner_id == user_id,
            models.Appointment.scheduled_start >= now,
            models.Appointment.scheduled_start < upcoming_end,
            models.Appointment.status.in_(active_statuses),
        )
    ) or 0
    active_count = db.scalar(
        select(func.count()).select_from(models.Appointment).where(
            models.Appointment.owner_id == user_id,
            models.Appointment.status.in_(active_statuses),
        )
    ) or 0
    reminders = list(
        db.scalars(
            select(models.MaintenanceReminder)
            .options(selectinload(models.MaintenanceReminder.vehicle))
            .where(
                models.MaintenanceReminder.owner_id == user_id,
                models.MaintenanceReminder.status == "pending",
            )
        ).all()
    )
    states = [reminder_read(reminder).due_state for reminder in reminders]
    return schemas.ScheduleSummary(
        today_appointments=today_count,
        upcoming_appointments=upcoming_count,
        active_appointments=active_count,
        overdue_reminders=states.count("overdue"),
        due_soon_reminders=states.count("due_soon"),
    )


@app.get(
    f"{settings.api_prefix}/inspection-template",
    response_model=list[schemas.InspectionTemplateItemRead],
)
def inspection_template() -> list[schemas.InspectionTemplateItemRead]:
    return [
        schemas.InspectionTemplateItemRead(
            category=category,
            item_key=item_key,
            label=label,
            position=position,
        )
        for position, (category, item_key, label) in enumerate(inspection.TEMPLATE_ITEMS, start=1)
    ]


@app.post(
    f"{settings.api_prefix}/work-orders/{{work_order_id}}/inspection",
    response_model=schemas.InspectionReportRead,
    status_code=status.HTTP_201_CREATED,
)
def create_inspection_report(
    work_order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InspectionReportRead:
    work_order = get_work_order_or_404(work_order_id, request.state.user.id, db)
    existing_id = db.scalar(
        select(models.InspectionReport.id).where(
            models.InspectionReport.work_order_id == work_order.id,
            models.InspectionReport.owner_id == request.state.user.id,
        )
    )
    if existing_id is not None:
        raise HTTPException(status_code=409, detail="Bu iş emri için kontrol formu zaten var")
    report = models.InspectionReport(
        owner_id=request.state.user.id,
        work_order_id=work_order.id,
        odometer=work_order.vehicle.mileage,
        items=[
            models.InspectionItem(
                category=category,
                item_key=item_key,
                label=label,
                position=position,
            )
            for position, (category, item_key, label) in enumerate(
                inspection.TEMPLATE_ITEMS, start=1
            )
        ],
    )
    db.add(report)
    db.flush()
    auth.add_audit_event(
        db,
        request.state.user.id,
        "inspection.created",
        entity_type="inspection",
        entity_id=report.id,
        event_data={"work_order_id": str(work_order.id), "item_count": len(report.items)},
    )
    db.commit()
    db.refresh(report)
    return inspection_read(report)


@app.get(
    f"{settings.api_prefix}/inspections",
    response_model=list[schemas.InspectionReportRead],
)
def list_inspection_reports(
    request: Request,
    db: Session = Depends(get_db),
) -> list[schemas.InspectionReportRead]:
    reports = list(
        db.scalars(
            select(models.InspectionReport)
            .options(selectinload(models.InspectionReport.items))
            .where(models.InspectionReport.owner_id == request.state.user.id)
            .order_by(models.InspectionReport.updated_at.desc())
        ).all()
    )
    return [inspection_read(report) for report in reports]


@app.get(
    f"{settings.api_prefix}/work-orders/{{work_order_id}}/inspection",
    response_model=schemas.InspectionReportRead,
)
def get_work_order_inspection(
    work_order_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InspectionReportRead:
    report = db.scalar(
        select(models.InspectionReport)
        .options(selectinload(models.InspectionReport.items))
        .where(
            models.InspectionReport.work_order_id == work_order_id,
            models.InspectionReport.owner_id == request.state.user.id,
        )
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Bu iş emri için kontrol formu bulunamadı")
    return inspection_read(report)


@app.patch(
    f"{settings.api_prefix}/inspections/{{inspection_id}}",
    response_model=schemas.InspectionReportRead,
)
def update_inspection_report(
    inspection_id: uuid.UUID,
    payload: schemas.InspectionReportUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> schemas.InspectionReportRead:
    report = get_inspection_or_404(inspection_id, request.state.user.id, db)
    was_completed = report.status == "completed"
    changes = payload.model_dump(exclude_unset=True, exclude={"items"})
    if "status" in changes and changes["status"] is None:
        raise HTTPException(status_code=422, detail="Kontrol formu durumu boş bırakılamaz")
    requested_status = changes.pop("status", None)
    if "technician_name" in changes and changes["technician_name"]:
        changes["technician_name"] = changes["technician_name"].strip() or None
    for field, value in changes.items():
        setattr(report, field, value)

    if payload.items is not None:
        item_map = {item.item_key: item for item in report.items}
        unknown_keys = sorted({item.item_key for item in payload.items} - set(item_map))
        if unknown_keys:
            raise HTTPException(
                status_code=422,
                detail=f"Bilinmeyen kontrol maddeleri: {', '.join(unknown_keys)}",
            )
        for item_update in payload.items:
            item = item_map[item_update.item_key]
            item.condition = item_update.condition
            item.measurement = item_update.measurement.strip() if item_update.measurement else None
            item.notes = item_update.notes.strip() if item_update.notes else None
            item.resolved = item_update.resolved if item_update.condition == "critical" else False
        if requested_status != "completed":
            if report.status == "completed":
                report.mechanic_approved = False
            report.status = "in_progress"
            report.completed_at = None

    if requested_status == "completed":
        errors = inspection.completion_errors(report.items, report.mechanic_approved)
        if errors:
            raise HTTPException(status_code=409, detail=" · ".join(errors))
        report.status = "completed"
        report.completed_at = datetime.now(timezone.utc)
    elif requested_status is not None:
        report.status = requested_status
        report.completed_at = None
    elif was_completed and payload.model_fields_set:
        report.status = "in_progress"
        report.completed_at = None

    vehicle = report.work_order.vehicle
    if report.odometer is not None and (vehicle.mileage is None or report.odometer > vehicle.mileage):
        vehicle.mileage = report.odometer

    db.flush()
    summary = inspection.summarize(report.items)
    auth.add_audit_event(
        db,
        request.state.user.id,
        "inspection.updated",
        entity_type="inspection",
        entity_id=report.id,
        event_data={
            "fields": sorted(payload.model_fields_set),
            "status": report.status,
            "health_score": summary["health_score"],
            "critical_count": summary["critical_count"],
        },
    )
    db.commit()
    db.refresh(report)
    return inspection_read(report)

