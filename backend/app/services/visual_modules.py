from datetime import UTC, datetime

from sqlalchemy import desc, func, select
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
HOUSING_SERIES_PREFIXES = ("FREDDIE_PMMS:", "FHFA_HPI:", "CENSUS:HOUSING:", "FRED:HOUSING:")
MACRO_SERIES_IDS = {"UNRATE", "CPIAUCSL", "FEDFUNDS", "DGS10", "RSAFS", "UMCSENT", "PAYEMS"}
MACRO_SERIES_PREFIXES = ("FRED:MACRO:", "FRED:RATES:", "FRED:LABOR:", "CENSUS:ECONOMIC:")
MARKET_SOURCE_KEYS = {"alpha-vantage", "finnhub", "newsapi", "bbc-news-rss", "gdelt-cloud"}
COMPANY_SOURCE_KEYS = {"sec-edgar-rss", "sec-data-apis", "alpha-vantage", "finnhub", "newsapi"}
QUOTE_SERIES_PREFIXES = ("ALPHA_VANTAGE:QUOTE:", "FINNHUB:QUOTE:")
QUOTE_METRIC_CHANGE_PERCENT = "CHANGE_PERCENT"
QUOTE_METRIC_PRICE = "PRICE"


def get_visual_modules(session: Session, *, user_id: int | None = None) -> VisualModulesResponse:
    reports = latest_reports_by_type(session, user_id=user_id)
    health_rows = list_source_health(session)
    observations = latest_observations_by_series(session)
    observation_history = recent_observations_by_series(session)
    watch_items = list_enabled_watch_items(session)
    generated_at = datetime.now(UTC).isoformat()

    modules = [
        build_daily_read_module(reports, health_rows),
        build_housing_module(reports, health_rows, observations, observation_history),
        build_markets_module(reports, health_rows, observations),
        build_companies_module(reports, health_rows, watch_items, observations),
        build_macro_module(reports, health_rows, observations, observation_history),
    ]

    return VisualModulesResponse(modules=modules, total=len(modules), generated_at=generated_at)


def latest_reports_by_type(session: Session, *, user_id: int | None = None) -> dict[str, Report]:
    statement = select(Report).order_by(desc(Report.created_at), desc(Report.id)).limit(40)
    if user_id is not None:
        statement = statement.where(Report.user_id == user_id)
    reports = session.scalars(statement).all()
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
    latest_ids = (
        select(func.max(EconomicObservation.id).label("latest_id"))
        .group_by(EconomicObservation.series_id)
        .subquery()
    )
    observations = session.scalars(
        select(EconomicObservation)
        .options(joinedload(EconomicObservation.source))
        .join(latest_ids, EconomicObservation.id == latest_ids.c.latest_id)
        .order_by(desc(EconomicObservation.retrieved_at), desc(EconomicObservation.released_at), desc(EconomicObservation.id))
    ).all()
    return {observation.series_id: observation for observation in observations}


def recent_observations_by_series(session: Session, *, limit: int = 1000, per_series: int = 8) -> dict[str, list[EconomicObservation]]:
    observations = session.scalars(
        select(EconomicObservation)
        .options(joinedload(EconomicObservation.source))
        .order_by(desc(EconomicObservation.retrieved_at), desc(EconomicObservation.released_at), desc(EconomicObservation.id))
        .limit(limit)
    ).all()
    history: dict[str, list[EconomicObservation]] = {}
    for observation in observations:
        series_history = history.setdefault(observation.series_id, [])
        if len(series_history) < per_series:
            series_history.append(observation)
    return history


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
    observation_history: dict[str, list[EconomicObservation]],
) -> VisualModule:
    report = reports.get("housing")
    housing_observations = [
        observation
        for series_id, observation in observations.items()
        if series_matches(series_id, HOUSING_SERIES_IDS, HOUSING_SERIES_PREFIXES)
    ]
    mortgage = (
        observations.get("FREDDIE_PMMS:30Y_FIXED")
        or observations.get("MORTGAGE30US")
        or observations.get("FREDDIE_PMMS:15Y_FIXED")
    )
    chart_history = preferred_observation_history(
        observation_history,
        ["FREDDIE_PMMS:30Y_FIXED", "MORTGAGE30US", "FREDDIE_PMMS:15Y_FIXED", "FHFAHPI"],
        HOUSING_SERIES_IDS,
        HOUSING_SERIES_PREFIXES,
    )

    return VisualModule(
        id="housing",
        title="Housing",
        summary=summary_from_report(report, "Tracks mortgage rates, affordability, permits, housing prices, and local housing signals."),
        primary_value=format_observation_value(mortgage) if mortgage else "No local data",
        primary_label=mortgage.series_name if mortgage else "mortgage / housing series",
        status="ready" if housing_observations else "no_local_data",
        trend="mixed",
        updated_at=format_datetime(latest_observation_time(housing_observations) or (report.as_of if report else None)),
        chart=chart_from_observation_history(chart_history, housing_observations),
        stats=[stat_from_observation(observation) for observation in housing_observations[:4]],
        sources=sources_from_health(filter_health(health_rows, {"fred-api", "freddie-mac-pmms", "fhfa-hpi", "census-economic-indicators"})),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the housing visual using my saved location and call out affordability, rates, inventory, and data gaps.",
    )


def build_markets_module(
    reports: dict[str, Report],
    health_rows: list[SourceHealth],
    observations: dict[str, EconomicObservation],
) -> VisualModule:
    report = reports.get("market_strategy")
    market_health = filter_health(health_rows, MARKET_SOURCE_KEYS)
    fresh_count = count_health(market_health, "fresh")
    quote_changes = quote_observations(observations, QUOTE_METRIC_CHANGE_PERCENT)

    return VisualModule(
        id="markets",
        title="Markets",
        summary=summary_from_report(report, "Tracks broad market tone, rates, sector pressure, volatility, commodities, and risk appetite."),
        primary_value=format_observation_value(quote_changes[0]) if quote_changes else str(fresh_count) if market_health else "--",
        primary_label=compact_quote_label(quote_changes[0]) if quote_changes else "fresh market sources",
        status="ready" if fresh_count else "needs_refresh",
        trend="mixed",
        updated_at=format_datetime(latest_health_time(market_health) or (report.as_of if report else None)),
        chart=chart_from_quote_changes(quote_changes)
        if quote_changes
        else chart_from_values([fresh_count, count_health(market_health, "stale"), count_health(market_health, "failed"), len(market_health), len(reports)]),
        stats=[
            *[stat_from_observation(observation) for observation in quote_changes[:3]],
            VisualStat(label="Fresh sources", value=str(fresh_count), detail="market/news providers"),
        ],
        sources=sources_from_health(market_health),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the market setup using live web first and corroborate it with connected market APIs.",
    )


def build_companies_module(
    reports: dict[str, Report],
    health_rows: list[SourceHealth],
    watch_items: list[WatchItem],
    observations: dict[str, EconomicObservation],
) -> VisualModule:
    report = reports.get("company_research")
    company_health = filter_health(health_rows, COMPANY_SOURCE_KEYS)
    active_alerts = [item for item in watch_items if item.last_matched_at is not None]
    quote_prices = quote_observations(observations, QUOTE_METRIC_PRICE)

    return VisualModule(
        id="companies",
        title="Companies",
        summary=summary_from_report(report, "Tracks saved companies, SEC filings, earnings news, catalysts, and watchlist alerts."),
        primary_value=str(len(quote_prices)) if quote_prices else str(len(watch_items)),
        primary_label="tickers with quotes" if quote_prices else "active watch items",
        status="ready" if watch_items or report else "no_local_data",
        trend="mixed" if active_alerts else "flat",
        updated_at=format_datetime(latest_watch_time(watch_items) or latest_health_time(company_health) or (report.as_of if report else None)),
        chart=chart_from_observations(quote_prices)
        if quote_prices
        else chart_from_values([len(watch_items), len(active_alerts), count_health(company_health, "fresh"), count_health(company_health, "failed"), len(company_health)]),
        stats=[
            *[stat_from_observation(observation) for observation in quote_prices[:3]],
            VisualStat(label="Watch items", value=str(len(watch_items)), detail="enabled"),
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
    observation_history: dict[str, list[EconomicObservation]],
) -> VisualModule:
    report = reports.get("macro")
    macro_observations = [
        observation
        for series_id, observation in observations.items()
        if series_matches(series_id, MACRO_SERIES_IDS, MACRO_SERIES_PREFIXES)
    ]
    headline_observation = (
        observations.get("FEDFUNDS")
        or observations.get("FRED:RATES:FEDFUNDS")
        or observations.get("DGS10")
        or observations.get("FRED:RATES:DGS10")
        or observations.get("UNRATE")
        or observations.get("FRED:LABOR:UNRATE")
    )
    chart_history = preferred_observation_history(
        observation_history,
        ["FEDFUNDS", "FRED:RATES:FEDFUNDS", "DGS10", "FRED:RATES:DGS10", "UNRATE", "FRED:LABOR:UNRATE"],
        MACRO_SERIES_IDS,
        MACRO_SERIES_PREFIXES,
    )

    return VisualModule(
        id="macro",
        title="Macro",
        summary=summary_from_report(report, "Connects inflation, rates, jobs, credit, policy, and consumer stress into a macro pulse."),
        primary_value=format_observation_value(headline_observation) if headline_observation else "--",
        primary_label=headline_observation.series_name if headline_observation else "macro observations",
        status="ready" if macro_observations else "no_local_data",
        trend="mixed",
        updated_at=format_datetime(latest_observation_time(macro_observations) or (report.as_of if report else None)),
        chart=chart_from_observation_history(chart_history, macro_observations),
        stats=[stat_from_observation(observation) for observation in macro_observations[:4]],
        sources=sources_from_health(filter_health(health_rows, {"fred-api", "us-census-economic-indicators"})),
        related_report_id=report.id if report else None,
        suggested_prompt="Explain the macro visual and the main trends in rates, inflation, jobs, credit, and consumer conditions.",
    )


def count_health(health_rows: list[SourceHealth], status: str) -> int:
    return sum(calculate_freshness_status(health) == status for health in health_rows)


def filter_health(health_rows: list[SourceHealth], source_keys: set[str]) -> list[SourceHealth]:
    return [health for health in health_rows if health.source_key in source_keys]


def series_matches(series_id: str, exact_ids: set[str], prefixes: tuple[str, ...]) -> bool:
    return series_id in exact_ids or any(series_id.startswith(prefix) for prefix in prefixes)


def quote_observations(observations: dict[str, EconomicObservation], metric: str) -> list[EconomicObservation]:
    quotes = [
        observation
        for series_id, observation in observations.items()
        if series_id.startswith(QUOTE_SERIES_PREFIXES) and quote_metric(series_id) == metric
    ]
    return sorted(quotes, key=lambda observation: observation.retrieved_at, reverse=True)


def quote_metric(series_id: str) -> str | None:
    parts = series_id.split(":")
    return parts[-1] if len(parts) >= 4 else None


def quote_ticker(series_id: str) -> str | None:
    parts = series_id.split(":")
    return parts[2] if len(parts) >= 4 else None


def compact_quote_label(observation: EconomicObservation) -> str:
    ticker = quote_ticker(observation.series_id)
    metric = quote_metric(observation.series_id)
    if ticker and metric == QUOTE_METRIC_CHANGE_PERCENT:
        return f"{ticker} daily move"
    if ticker and metric == QUOTE_METRIC_PRICE:
        return f"{ticker} latest price"
    return compact_observation_label(observation)


def preferred_observation_history(
    observation_history: dict[str, list[EconomicObservation]],
    preferred_series_ids: list[str],
    exact_ids: set[str],
    prefixes: tuple[str, ...],
) -> list[EconomicObservation]:
    for series_id in preferred_series_ids:
        history = observation_history.get(series_id, [])
        if history:
            return list(reversed(history))
    for series_id, history in observation_history.items():
        if history and series_matches(series_id, exact_ids, prefixes):
            return list(reversed(history))
    return []


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


def chart_from_observation_history(
    history: list[EconomicObservation],
    fallback_observations: list[EconomicObservation],
) -> VisualChart:
    if history:
        return VisualChart(
            kind="line" if len(history) > 1 else "bar",
            points=[
                VisualChartPoint(label=format_chart_label(observation), value=float(abs(observation.value)))
                for observation in history[-8:]
            ],
        )
    return chart_from_observations(fallback_observations)


def chart_from_observations(observations: list[EconomicObservation]) -> VisualChart:
    if not observations:
        return chart_from_values([1, 1, 1, 1, 1])

    return VisualChart(
        kind="bar",
        points=[
            VisualChartPoint(label=compact_chart_label(observation), value=float(abs(observation.value)))
            for observation in observations[:6]
        ],
    )


def chart_from_quote_changes(observations: list[EconomicObservation]) -> VisualChart:
    if not observations:
        return chart_from_values([1, 1, 1, 1, 1])
    return VisualChart(
        kind="bar",
        points=[
            VisualChartPoint(label=quote_ticker(observation.series_id) or compact_chart_label(observation), value=float(abs(observation.value)))
            for observation in observations[:6]
        ],
    )


def stat_from_observation(observation: EconomicObservation) -> VisualStat:
    return VisualStat(
        label=compact_observation_label(observation),
        value=format_observation_value(observation),
        detail=f"{observation.series_name} / {observation.period}",
    )


def format_observation_value(observation: EconomicObservation | None) -> str:
    if observation is None:
        return "--"
    value = f"{observation.value:.2f}".rstrip("0").rstrip(".")
    unit = observation.unit or ""
    if unit.lower() in {"percent", "%"} or looks_like_percent_observation(observation):
        return f"{value}%"
    if unit.lower() == "currency":
        return f"${value}"
    if unit.lower() == "index":
        return value
    return f"{value} {unit}".strip()


def looks_like_percent_observation(observation: EconomicObservation) -> bool:
    name = (observation.series_name or "").lower()
    series_id = observation.series_id.upper()
    return (
        observation.value <= 100
        and (
            series_id in {"FEDFUNDS", "DGS10", "UNRATE", "MORTGAGE30US"}
            or series_id.endswith((":FEDFUNDS", ":DGS10", ":UNRATE", ":CHANGE_PERCENT"))
            or "rate" in name
            or "percent" in name
        )
    )


def compact_observation_label(observation: EconomicObservation) -> str:
    ticker = quote_ticker(observation.series_id)
    metric = quote_metric(observation.series_id)
    if ticker and metric == QUOTE_METRIC_PRICE:
        return f"{ticker} price"
    if ticker and metric == QUOTE_METRIC_CHANGE_PERCENT:
        return f"{ticker} daily move"

    name = observation.series_name or observation.series_id
    replacements = {
        "Freddie Mac PMMS - ": "",
        "FHFA All-Transactions HPI - ": "HPI - ",
        "30-Year Fixed-Rate Mortgage": "30Y mortgage",
        "15-Year Fixed-Rate Mortgage": "15Y mortgage",
    }
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name[:42]


def compact_chart_label(observation: EconomicObservation) -> str:
    ticker = quote_ticker(observation.series_id)
    if ticker:
        return ticker
    return compact_observation_label(observation)[:12]


def format_chart_label(observation: EconomicObservation) -> str:
    period = observation.period or observation.vintage or ""
    if len(period) >= 10 and period[4] == "-" and period[7] == "-":
        return period[5:10]
    if len(period) >= 7:
        return period[:7]
    return compact_chart_label(observation)


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
    return clean_visual_summary(report.summary or first_body_sentence(report.body)) or fallback


def first_body_sentence(body: str) -> str:
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), "")
    if first_line.startswith("#"):
        non_heading = next((line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("#")), "")
        first_line = non_heading or first_line
    return clean_visual_summary(first_line)[:260]


def clean_visual_summary(value: str | None) -> str:
    if not value:
        return ""
    lines = []
    for line in value.splitlines():
        clean = line.strip()
        if not clean:
            continue
        clean = clean.lstrip("-* ").strip()
        if clean.startswith("#") or clean.lower().startswith("coordinator selected"):
            continue
        lines.append(clean)
        if len(" ".join(lines)) > 260:
            break
    return " ".join(lines).replace("**", "").strip()[:260]
