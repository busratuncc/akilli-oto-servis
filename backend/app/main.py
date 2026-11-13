from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas, services
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
    work_order.dtc_codes = [models.DtcCode(**item.model_dump()) for item in payload.dtc_codes]
    db.add(work_order)
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


@app.post(f"{settings.api_prefix}/ai/extract-preview", response_model=schemas.ExtractionPreview)
def preview_extraction(payload: schemas.ExtractionRequest) -> schemas.ExtractionPreview:
    return services.extract_preview(payload.text)


@app.post(f"{settings.api_prefix}/cases/search", response_model=list[schemas.CaseSearchResult])
def search_cases(payload: schemas.CaseSearchRequest, db: Session = Depends(get_db)) -> list[schemas.CaseSearchResult]:
    results = services.search_cases(db, payload)
    return [
        schemas.CaseSearchResult(
            work_order=schemas.WorkOrderRead.model_validate(work_order),
            vehicle=schemas.VehicleRead.model_validate(work_order.vehicle),
            match_reason=reason,
        )
        for work_order, reason in results
    ]

