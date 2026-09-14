from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import EconomicObservation, Report, SourceHealth, WatchItem
from app.schemas.visual import (
    VisualChart,
    VisualChartPoint,
    VisualModule,
    VisualModulesResponse,
    VisualSource,
    VisualStat,
)
from app.services.ingestion_status import calculate_freshness_status, format_datetime


HOUSING_SERIES_IDS = {"MORTGAGE30US", "FHFAHPI", "MSPUS", "PERMIT", "HOUST", "HSN1F"}
MACRO_SERIES_IDS = {"UNRATE", "CPIAUCSL", "FEDFUNDS", "DGS10", "RSAFS", "UMCSENT", "PAYEMS"}
MARKET_SOURCE_KEYS = {"alpha-vantage", "finnhub", "newsapi", "bbc-news-rss", "gdelt-cloud"}
COMPANY_SOURCE_KEYS = {"sec-edgar-rss", "sec-data-apis", "alpha-vantage", "finnhub", "newsapi"}


def get_visual_modules(session: Session) -> VisualModulesResponse:
    reports = latest_reports_by_type(session)
    health_rows = list_source_health(session)
    observations = latest_observations_by_series(session)
    watch_items = list_enabled_watch_items(session)
    generated_at = datetime.now(UTC).isoformat()

    modules = [
        build_daily_read_module(reports, health_rows),
        build_housing_module(reports, health_rows, observations),
        build_markets_module(reports, health_rows),
        build_companies_module(reports, health_rows, watch_items),
        build_macro_module(reports, health_rows, observations),
    ]

    return VisualModulesResponse(modules=modules, total=len(modules), generated_at=generated_at)


def latest_reports_by_type(session: Session) -> dict[str, Report]:
    reports = session.scalars(select(Report).order_by(desc(Report.created_at), desc(Report.id)).limit(40)).all()
    latest: dict[str, Report] = {}
    for report in reports:
        if report.status == "archived":
            continue
        latest.setdefault(report.report_type, report)
    return latest


def list_source_health(session: Session) -> list[SourceHealth]:
    return list(
        session.scalars(
            select(SourceHealth).options(joinedload(SourceHealth.source)).order_by(SourceHealth.source_key)
        ).all()
    )


def latest_observations_by_series(session: Session) -> dict[str, EconomicObservation]:
    observations = session.scalars(
        select(EconomicObservation)
        .options(joinedload(EconomicObservation.source))
        .order_by(desc(EconomicObservation.retrieved_at), desc(EconomicObservation.released_at), desc(EconomicObservation.id))
        .limit(120)
    ).all()
    latest: dict[str, EconomicObservation] = {}
    for observation in observations:
        latest.setdefault(observation.series_id, observation)
    return latest


def list_enabled_watch_items(session: Session) -> list[WatchItem]:
    return list(session.scalars(select(WatchItem).where(WatchItem.enabled.is_(True)).order_by(desc(WatchItem.updated_at))).all())


def build_daily_read_module(reports: dict[str, Report], health_rows: list[SourceHealth]) -> VisualModule:
    report = reports.get("daily_briefing")
    fresh_count = count_health(health_rows, "fresh")
    failed_count = count_health(health_rows, "failed")
    source_count = len(health_rows)
    status = "ready" if report else "needs_refresh"

    return VisualModule(
        id="daily_read",
        title="Daily Read",
        summary=summary_from_report(report, "A personal daily brief will appear after the refresh and brief generation run."),
        primary_value="Ready" if report else "Open",
        primary_label="latest brief" if report else "needs generation",
        status=status,
        trend="mixed" if failed_count else "flat",
        updated_at=format_datetime(report.as_of or report.created_at if report else latest_health_time(health_rows)),
        chart=chart_from_values([fresh_count, failed_count, source_count, len(reports), 1 if report else 0]),
        stats=[
            VisualStat(label="Fresh sources", value=str(fresh_count), detail="source health"),
            VisualStat(label="Needs attention", value=str(failed_count), detail="failed source checks"),
            VisualStat(label="Saved reports", value=str(len(reports)), detail="latest available report types"),
        ],
        sources=sources_from_health(health_rows, limit=5),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain today's daily read and what changed most since the last refresh.",
    )


def build_housing_module(
    reports: dict[str, Report],
    health_rows: list[SourceHealth],
    observations: dict[str, EconomicObservation],
) -> VisualModule:
    report = reports.get("housing")
    housing_observations = [observation for series_id, observation in observations.items() if series_id in HOUSING_SERIES_IDS]
    mortgage = observations.get("MORTGAGE30US")

    return VisualModule(
        id="housing",
        title="Housing",
        summary=summary_from_report(report, "Tracks mortgage rates, affordability, permits, housing prices, and local housing signals."),
        primary_value=format_observation_value(mortgage) if mortgage else "No local data",
        primary_label=mortgage.series_name if mortgage else "mortgage / housing series",
        status="ready" if housing_observations else "no_local_data",
        trend="mixed",
        updated_at=format_datetime(latest_observation_time(housing_observations) or (report.as_of if report else None)),
        chart=chart_from_observations(housing_observations),
        stats=[stat_from_observation(observation) for observation in housing_observations[:4]],
        sources=sources_from_health(filter_health(health_rows, {"fred-api", "freddie-mac-pmms", "fhfa-house-price-index", "us-census-economic-indicators"})),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the housing visual using my saved location and call out affordability, rates, inventory, and data gaps.",
    )


def build_markets_module(reports: dict[str, Report], health_rows: list[SourceHealth]) -> VisualModule:
    report = reports.get("market_strategy")
    market_health = filter_health(health_rows, MARKET_SOURCE_KEYS)
    fresh_count = count_health(market_health, "fresh")

    return VisualModule(
        id="markets",
        title="Markets",
        summary=summary_from_report(report, "Tracks broad market tone, rates, sector pressure, volatility, commodities, and risk appetite."),
        primary_value=str(fresh_count) if market_health else "--",
        primary_label="fresh market sources",
        status="ready" if fresh_count else "needs_refresh",
        trend="mixed",
        updated_at=format_datetime(latest_health_time(market_health) or (report.as_of if report else None)),
        chart=chart_from_values([fresh_count, count_health(market_health, "stale"), count_health(market_health, "failed"), len(market_health), len(reports)]),
        stats=[
            VisualStat(label="Fresh", value=str(fresh_count), detail="market/news sources"),
            VisualStat(label="Failed", value=str(count_health(market_health, "failed")), detail="market/news sources"),
            VisualStat(label="Saved report", value="Yes" if report else "No", detail="market strategy"),
        ],
        sources=sources_from_health(market_health),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the market setup using live web first and corroborate it with connected market APIs.",
    )


def build_companies_module(
    reports: dict[str, Report],
    health_rows: list[SourceHealth],
    watch_items: list[WatchItem],
) -> VisualModule:
    report = reports.get("company_research")
    company_health = filter_health(health_rows, COMPANY_SOURCE_KEYS)
    active_alerts = [item for item in watch_items if item.last_matched_at is not None]

    return VisualModule(
        id="companies",
        title="Companies",
        summary=summary_from_report(report, "Tracks saved companies, SEC filings, earnings news, catalysts, and watchlist alerts."),
        primary_value=str(len(watch_items)),
        primary_label="active watch items",
        status="ready" if watch_items or report else "no_local_data",
        trend="mixed" if active_alerts else "flat",
        updated_at=format_datetime(latest_watch_time(watch_items) or latest_health_time(company_health) or (report.as_of if report else None)),
        chart=chart_from_values([len(watch_items), len(active_alerts), count_health(company_health, "fresh"), count_health(company_health, "failed"), len(company_health)]),
        stats=[
            VisualStat(label="Watch items", value=str(len(watch_items)), detail="enabled"),
            VisualStat(label="Recent matches", value=str(len(active_alerts)), detail="watch alerts"),
            VisualStat(label="Fresh sources", value=str(count_health(company_health, "fresh")), detail="company data providers"),
        ],
        sources=sources_from_health(company_health),
        related_report_id=report.id if report else None,
        related_watch_item_ids=[item.id for item in watch_items[:5]],
        suggested_prompt="Explain what changed for my saved companies and watchlist without giving buy or sell instructions.",
    )


def build_macro_module(
    reports: dict[str, Report],
    health_rows: list[SourceHealth],
    observations: dict[str, EconomicObservation],
) -> VisualModule:
    report = reports.get("macro")
    macro_observations = [observation for series_id, observation in observations.items() if series_id in MACRO_SERIES_IDS]
    headline_observation = observations.get("FEDFUNDS") or observations.get("DGS10") or observations.get("UNRATE")

    return VisualModule(
        id="macro",
        title="Macro",
        summary=summary_from_report(report, "Connects inflation, rates, jobs, credit, policy, and consumer stress into a macro pulse."),
        primary_value=format_observation_value(headline_observation) if headline_observation else "--",
        primary_label=headline_observation.series_name if headline_observation else "macro observations",
        status="ready" if macro_observations else "no_local_data",
        trend="mixed",
        updated_at=format_datetime(latest_observation_time(macro_observations) or (report.as_of if report else None)),
        chart=chart_from_observations(macro_observations),
        stats=[stat_from_observation(observation) for observation in macro_observations[:4]],
        sources=sources_from_health(filter_health(health_rows, {"fred-api", "us-census-economic-indicators"})),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the macro visual and the main trends in rates, inflation, jobs, credit, and consumer conditions.",
    )


def count_health(health_rows: list[SourceHealth], status: str) -> int:
    return sum(calculate_freshness_status(health) == status for health in health_rows)


def filter_health(health_rows: list[SourceHealth], source_keys: set[str]) -> list[SourceHealth]:
    return [health for health in health_rows if health.source_key in source_keys]


def sources_from_health(health_rows: list[SourceHealth], *, limit: int = 4) -> list[VisualSource]:
    return [
        VisualSource(
            name=health.source.name if health.source else health.source_key,
            status=calculate_freshness_status(health),
            retrieved_at=format_datetime(health.last_success_at or health.last_attempt_at),
            description=health.latest_item_title or health.last_error,
        )
        for health in health_rows[:limit]
    ]


def chart_from_values(values: list[int | float]) -> VisualChart:
    return VisualChart(
        kind="bar",
        points=[VisualChartPoint(label=f"P{index + 1}", value=float(max(value, 0))) for index, value in enumerate(values)],
    )


def chart_from_observations(observations: list[EconomicObservation]) -> VisualChart:
    if not observations:
        return chart_from_values([1, 1, 1, 1, 1])

    return VisualChart(
        kind="bar",
        points=[
            VisualChartPoint(label=observation.series_id[:8], value=float(abs(observation.value)))
            for observation in observations[:6]
        ],
    )


def stat_from_observation(observation: EconomicObservation) -> VisualStat:
    return VisualStat(
        label=observation.series_id,
        value=format_observation_value(observation),
        detail=f"{observation.series_name} / {observation.period}",
    )


def format_observation_value(observation: EconomicObservation | None) -> str:
    if observation is None:
        return "--"
    value = f"{observation.value:.2f}".rstrip("0").rstrip(".")
    return f"{value}{observation.unit or ''}"


def latest_observation_time(observations: list[EconomicObservation]) -> datetime | None:
    times = [observation.retrieved_at for observation in observations if observation.retrieved_at is not None]
    return max(times) if times else None


def latest_health_time(health_rows: list[SourceHealth]) -> datetime | None:
    times = [health.last_success_at or health.last_attempt_at for health in health_rows if health.last_success_at or health.last_attempt_at]
    return max(times) if times else None


def latest_watch_time(watch_items: list[WatchItem]) -> datetime | None:
    times = [item.last_matched_at or item.last_checked_at or item.updated_at for item in watch_items]
    return max(times) if times else None


def summary_from_report(report: Report | None, fallback: str) -> str:
    if report is None:
        return fallback
    return report.summary or first_body_sentence(report.body) or fallback


def first_body_sentence(body: str) -> str:
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    return first_line[:260]
