from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ingestion import (
    DailyScheduleConfig,
    IngestionRunHistoryResponse,
    IngestionRunRequest,
    IngestionRunResponse,
    LatestItemsResponse,
    SourceHealthResponse,
)
from app.services.ingestion_runner import (
    get_daily_schedule_config,
    run_due_daily_workflow,
    run_ingestion,
    update_daily_schedule_config,
)
from app.services.ingestion_status import get_source_health, list_ingestion_runs, list_latest_items


router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=IngestionRunResponse)
def trigger_ingestion_run(
    request: IngestionRunRequest,
    db: Session = Depends(get_db),
) -> IngestionRunResponse:
    return run_ingestion(db, request)


@router.get("/health", response_model=SourceHealthResponse)
def read_source_health(db: Session = Depends(get_db)) -> SourceHealthResponse:
    return get_source_health(db)


@router.get("/runs", response_model=IngestionRunHistoryResponse)
def read_ingestion_runs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> IngestionRunHistoryResponse:
    return list_ingestion_runs(db, limit=limit)


@router.get("/latest-items", response_model=LatestItemsResponse)
def read_latest_items(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> LatestItemsResponse:
    return list_latest_items(db, limit=limit)


@router.get("/schedule", response_model=DailyScheduleConfig)
def get_ingestion_schedule(db: Session = Depends(get_db)) -> DailyScheduleConfig:
    return get_daily_schedule_config(db)


@router.post("/schedule", response_model=DailyScheduleConfig)
def update_ingestion_schedule(config: DailyScheduleConfig, db: Session = Depends(get_db)) -> DailyScheduleConfig:
    return update_daily_schedule_config(db, config)


@router.post("/schedule/run-due", response_model=DailyScheduleConfig)
def run_due_ingestion_schedule(db: Session = Depends(get_db)) -> DailyScheduleConfig:
    return run_due_daily_workflow(db)
