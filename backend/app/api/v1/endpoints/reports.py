from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import (
    CompanyResearchRequest,
    DailyBriefingRequest,
    HousingReportRequest,
    MacroReportRequest,
    MarketStrategyRequest,
    ReportCreateRequest,
    ReportDeleteResponse,
    ReportListResponse,
    ReportResponse,
    ReportType,
)
from app.services.auth import optional_user_from_authorization, require_user
from app.services.reports import (
    archive_report,
    create_report,
    delete_report,
    generate_company_research,
    generate_daily_briefing,
    generate_housing_report,
    generate_macro_report,
    generate_market_strategy,
    get_report,
    list_reports,
    regenerate_report,
)


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=201)
def create_research_report(
    request: ReportCreateRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return create_report(db, request, user_id=user.id) if user else create_report(db, request)


@router.post("/daily-briefing", response_model=ReportResponse, status_code=201)
def create_daily_briefing(
    request: DailyBriefingRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return generate_daily_briefing(db, request, user_id=user.id) if user else generate_daily_briefing(db, request)


@router.post("/company-research", response_model=ReportResponse, status_code=201)
def create_company_research(
    request: CompanyResearchRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return generate_company_research(db, request, user_id=user.id) if user else generate_company_research(db, request)


@router.post("/market-strategy", response_model=ReportResponse, status_code=201)
def create_market_strategy(
    request: MarketStrategyRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return generate_market_strategy(db, request, user_id=user.id) if user else generate_market_strategy(db, request)


@router.post("/housing", response_model=ReportResponse, status_code=201)
def create_housing_report(
    request: HousingReportRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return generate_housing_report(db, request, user_id=user.id) if user else generate_housing_report(db, request)


@router.post("/macro", response_model=ReportResponse, status_code=201)
def create_macro_report(
    request: MacroReportRequest,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return generate_macro_report(db, request, user_id=user.id) if user else generate_macro_report(db, request)


@router.get("", response_model=ReportListResponse)
def read_reports(
    limit: int = Query(default=25, ge=1, le=100),
    report_type: ReportType | None = None,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    user = optional_user_from_authorization(db, authorization)
    return list_reports(db, limit=limit, report_type=report_type, user_id=user.id if user else None)


@router.get("/{report_id}", response_model=ReportResponse)
def read_report(
    report_id: int,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return get_report(db, report_id, user_id=user.id if user else None)


@router.post("/{report_id}/archive", response_model=ReportResponse)
def archive_research_report(
    report_id: int,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return archive_report(db, report_id, user_id=user.id if user else None)


@router.post("/{report_id}/regenerate", response_model=ReportResponse, status_code=201)
def regenerate_research_report(
    report_id: int,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    user = optional_user_from_authorization(db, authorization)
    return regenerate_report(db, report_id, user_id=user.id if user else None)


@router.delete("/{report_id}", response_model=ReportDeleteResponse)
def delete_research_report(
    report_id: int,
    authorization: str | None = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReportDeleteResponse:
    user = optional_user_from_authorization(db, authorization)
    return delete_report(db, report_id, user_id=user.id if user else None)
