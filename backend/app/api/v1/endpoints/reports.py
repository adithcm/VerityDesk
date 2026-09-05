from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import (
    CompanyResearchRequest,
    DailyBriefingRequest,
    MarketStrategyRequest,
    ReportCreateRequest,
    ReportDeleteResponse,
    ReportListResponse,
    ReportResponse,
    ReportType,
)
from app.services.reports import (
    create_report,
    delete_report,
    generate_company_research,
    generate_daily_briefing,
    generate_market_strategy,
    get_report,
    list_reports,
)


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=201)
def create_research_report(
    request: ReportCreateRequest,
    db: Session = Depends(get_db),
) -> ReportResponse:
    return create_report(db, request)


@router.post("/daily-briefing", response_model=ReportResponse, status_code=201)
def create_daily_briefing(
    request: DailyBriefingRequest,
    db: Session = Depends(get_db),
) -> ReportResponse:
    return generate_daily_briefing(db, request)


@router.post("/company-research", response_model=ReportResponse, status_code=201)
def create_company_research(
    request: CompanyResearchRequest,
    db: Session = Depends(get_db),
) -> ReportResponse:
    return generate_company_research(db, request)


@router.post("/market-strategy", response_model=ReportResponse, status_code=201)
def create_market_strategy(
    request: MarketStrategyRequest,
    db: Session = Depends(get_db),
) -> ReportResponse:
    return generate_market_strategy(db, request)


@router.get("", response_model=ReportListResponse)
def read_reports(
    limit: int = Query(default=25, ge=1, le=100),
    report_type: ReportType | None = None,
    db: Session = Depends(get_db),
) -> ReportListResponse:
    return list_reports(db, limit=limit, report_type=report_type)


@router.get("/{report_id}", response_model=ReportResponse)
def read_report(report_id: int, db: Session = Depends(get_db)) -> ReportResponse:
    return get_report(db, report_id)


@router.delete("/{report_id}", response_model=ReportDeleteResponse)
def delete_research_report(report_id: int, db: Session = Depends(get_db)) -> ReportDeleteResponse:
    return delete_report(db, report_id)
