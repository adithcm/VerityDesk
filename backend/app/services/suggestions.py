from datetime import UTC, datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Article, EconomicObservation, Report
from app.schemas.suggestion import ProactiveSuggestion, ProactiveSuggestionsResponse
from app.services.personalization import get_or_create_preferences


GUARDRAIL_NOTE = "Research only. Not financial advice or a buy, sell, or hold recommendation."
DEFAULT_WATCHLIST = ["SPY", "QQQ", "TLT"]
HOUSING_DOMAINS = {"Housing and Real Estate", "Markets and Rates", "Banking and Credit"}
MACRO_DOMAINS = {"U.S. Economy and Policy", "Consumer and Labor", "Markets and Rates", "Banking and Credit"}
MARKET_DOMAINS = {"Markets and Rates", "Companies and Earnings", "Commodities and Energy", "Technology and AI"}


def get_proactive_suggestions(session: Session, *, limit: int = 8) -> ProactiveSuggestionsResponse:
    preferences = get_or_create_preferences(session)
    articles = recent_articles(session)
    observations = recent_observations(session)
    reports = recent_reports(session)
    latest_report_types = {report.report_type for report in reports[:8]}
    domains = ranked_domains(articles)
    tickers = preferences.watchlist_tickers or ranked_tickers(articles) or DEFAULT_WATCHLIST
    preferred_regions = preferences.preferred_regions or []

    suggestions = [
        daily_briefing_suggestion(domains, tickers, preferred_regions),
        market_strategy_suggestion(tickers, domains),
        watchlist_question_suggestion(tickers, domains),
        housing_suggestion(domains, latest_report_types, observations, preferred_regions),
        macro_suggestion(domains, latest_report_types, observations),
        follow_up_suggestion(reports),
        source_gap_suggestion(articles, observations),
    ]
    ranked = sorted(unique_suggestions(suggestions), key=lambda item: (-item.priority, item.title))
    return ProactiveSuggestionsResponse(
        suggestions=ranked[:limit],
        total=min(len(ranked), limit),
        generated_at=datetime.now(UTC).isoformat(),
    )


def recent_articles(session: Session, limit: int = 30) -> list[Article]:
    return session.scalars(
        select(Article).order_by(desc(Article.retrieved_at), desc(Article.published_at), desc(Article.id)).limit(limit)
    ).all()


def recent_observations(session: Session, limit: int = 20) -> list[EconomicObservation]:
    return session.scalars(
        select(EconomicObservation)
        .order_by(desc(EconomicObservation.retrieved_at), desc(EconomicObservation.released_at), desc(EconomicObservation.id))
        .limit(limit)
    ).all()


def recent_reports(session: Session, limit: int = 20) -> list[Report]:
    return session.scalars(
        select(Report)
        .where(Report.status != "archived")
        .order_by(desc(Report.created_at), desc(Report.id))
        .limit(limit)
    ).all()


def ranked_domains(articles: list[Article]) -> list[str]:
    counts: dict[str, int] = {}
    for article in articles:
        for domain in article.domains or []:
            counts[domain] = counts.get(domain, 0) + 1
    return [domain for domain, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]


def ranked_tickers(articles: list[Article]) -> list[str]:
    counts: dict[str, int] = {}
    for article in articles:
        for ticker in article.tickers or []:
            normalized = ticker.strip().upper()
            if normalized:
                counts[normalized] = counts.get(normalized, 0) + 1
    return [ticker for ticker, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:5]]


def daily_briefing_suggestion(
    domains: list[str],
    tickers: list[str],
    preferred_regions: list[str],
) -> ProactiveSuggestion:
    focus = domains[:3] or ["markets", "macro", "company news"]
    preference_notes = [*tickers[:3], *preferred_regions[:2]]
    preference_text = f" with attention to {', '.join(preference_notes)}" if preference_notes else ""
    return ProactiveSuggestion(
        id="daily-briefing",
        kind="report",
        title="Generate Today's Briefing",
        prompt=f"Create a concise daily briefing focused on {', '.join(focus)}{preference_text}.",
        action="generate_daily_briefing",
        priority=5,
        domains=domains[:5],
        tickers=tickers[:5],
        regions=preferred_regions[:5],
        reasons=["Fresh daily context is most useful before asking detailed questions."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def market_strategy_suggestion(tickers: list[str], domains: list[str]) -> ProactiveSuggestion:
    matched_domains = [domain for domain in domains if domain in MARKET_DOMAINS]
    return ProactiveSuggestion(
        id="market-strategy",
        kind="report",
        title="Review Market Setup",
        prompt="Generate a market strategy note with base, upside, and downside scenarios.",
        action="generate_market_strategy",
        priority=4 if matched_domains else 3,
        domains=matched_domains or ["Markets and Rates"],
        tickers=tickers[:3],
        reasons=["Scenario framing helps compare risks without producing buy or sell instructions."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def watchlist_question_suggestion(tickers: list[str], domains: list[str]) -> ProactiveSuggestion:
    return ProactiveSuggestion(
        id="watchlist-question",
        kind="question",
        title="Ask About Your Watchlist",
        prompt=f"What changed recently for {', '.join(tickers[:3])}, and what should I watch next?",
        action="run_agent_query",
        priority=4,
        domains=domains[:3] or ["Markets and Rates"],
        tickers=tickers[:3],
        reasons=["Your watchlist gives the agent a focused starting point."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def housing_suggestion(
    domains: list[str],
    latest_report_types: set[str],
    observations: list[EconomicObservation],
    preferred_regions: list[str],
) -> ProactiveSuggestion:
    has_housing_signal = any(domain in HOUSING_DOMAINS for domain in domains) or any(
        observation.series_id in {"MORTGAGE30US", "CSUSHPINSA", "HOUST", "PERMIT"} for observation in observations
    )
    region_text = f" for {', '.join(preferred_regions[:2])}" if preferred_regions else ""
    return ProactiveSuggestion(
        id="housing-report",
        kind="report",
        title="Check Housing Conditions",
        prompt=f"Generate a housing report{region_text} covering rates, affordability, supply, demand, and credit conditions.",
        action="generate_housing_report",
        priority=4 if has_housing_signal and "housing" not in latest_report_types else 2,
        domains=["Housing and Real Estate", "Markets and Rates", "Banking and Credit"],
        regions=preferred_regions[:5],
        reasons=["Housing signals can change market and consumer context."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def macro_suggestion(
    domains: list[str],
    latest_report_types: set[str],
    observations: list[EconomicObservation],
) -> ProactiveSuggestion:
    has_macro_signal = any(domain in MACRO_DOMAINS for domain in domains) or len(observations) > 0
    return ProactiveSuggestion(
        id="macro-report",
        kind="report",
        title="Review Macro Context",
        prompt="Generate a macro report covering rates, labor, policy, credit, inflation context, and risks.",
        action="generate_macro_report",
        priority=4 if has_macro_signal and "macro" not in latest_report_types else 2,
        domains=["U.S. Economy and Policy", "Consumer and Labor", "Markets and Rates"],
        reasons=["Macro context helps explain broad moves and uncertainty."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def follow_up_suggestion(reports: list[Report]) -> ProactiveSuggestion:
    latest_report = reports[0] if reports else None
    follow_ups = list((latest_report.report_metadata or {}).get("follow_up_questions") or []) if latest_report else []
    prompt = follow_ups[0] if follow_ups else "What are the biggest open questions from my latest saved reports?"
    return ProactiveSuggestion(
        id="report-follow-up",
        kind="question",
        title="Follow Up On Saved Reports",
        prompt=prompt,
        action="run_agent_query",
        priority=3 if latest_report else 2,
        domains=list(latest_report.domains or [])[:3] if latest_report else [],
        tickers=list(latest_report.tickers or [])[:3] if latest_report else [],
        reasons=["Saved reports often contain open questions worth revisiting."],
        guardrail_note=GUARDRAIL_NOTE,
    )


def source_gap_suggestion(articles: list[Article], observations: list[EconomicObservation]) -> ProactiveSuggestion:
    reasons = []
    if not articles:
        reasons.append("No recent article evidence is available yet.")
    if not observations:
        reasons.append("No recent official economic observations are available yet.")
    if not reasons:
        reasons.append("Review source freshness before relying on generated reports.")
    return ProactiveSuggestion(
        id="source-gap-check",
        kind="evidence_gap",
        title="Review Source Coverage",
        prompt="Check source freshness and run ingestion before generating new reports if needed.",
        action="review_sources",
        priority=3 if not articles or not observations else 1,
        domains=[],
        reasons=reasons,
        guardrail_note=GUARDRAIL_NOTE,
    )


def unique_suggestions(suggestions: list[ProactiveSuggestion]) -> list[ProactiveSuggestion]:
    seen: set[str] = set()
    unique: list[ProactiveSuggestion] = []
    for suggestion in suggestions:
        if suggestion.id in seen:
            continue
        seen.add(suggestion.id)
        unique.append(suggestion)
    return unique
