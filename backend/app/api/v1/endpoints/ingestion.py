from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ingestion import DailyScheduleConfig, IngestionRunRequest, IngestionRunResponse
from app.services.ingestion_runner import (
    get_daily_schedule_config,
    run_ingestion,
    update_daily_schedule_config,
)


router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run", response_model=IngestionRunResponse)
def trigger_ingestion_run(
    request: IngestionRunRequest,
    db: Session = Depends(get_db),
) -> IngestionRunResponse:
    return run_ingestion(db, request)


@router.get("/schedule", response_model=DailyScheduleConfig)
def get_ingestion_schedule() -> DailyScheduleConfig:
    return get_daily_schedule_config()


@router.post("/schedule", response_model=DailyScheduleConfig)
def update_ingestion_schedule(config: DailyScheduleConfig) -> DailyScheduleConfig:
    return update_daily_schedule_config(config)
