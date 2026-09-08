from __future__ import annotations

from dataclasses import dataclass

from app.agents.model_client import ResearchSummarizer, TemplateResearchSummarizer
from app.schemas.agent import AgentCitation, AgentClaim, AgentContext, AgentResult, ConfidenceLevel
from app.schemas.evidence_packet import EvidencePacket, EvidencePacketItem
from app.services.research_evidence import (
    ArticleEvidence,
    EconomicObservationEvidence,
    EvidenceQuery,
    ResearchEvidenceRepository,
    SourceHealthEvidence,
)


@dataclass(frozen=True)
class DomainAgentConfig:
    name: str
    focus: str
    domains: tuple[str, ...] = ()
    series_ids: tuple[str, ...] = ()
    default_time_window: str = "month"
    article_limit: int = 5
    observation_limit: int = 5
    expected_source_ids: tuple[str, ...] = ()


class EvidenceBackedDomainAgent:
    def __init__(
        self,
        repository: ResearchEvidenceRepository,
        summarizer: ResearchSummarizer | None = None,
    ) -> None:
        self.repository = repository
        self.summarizer = summarizer or TemplateResearchSummarizer()

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def config(self) -> DomainAgentConfig:
        raise NotImplementedError

    def run(self, context: AgentContext) -> AgentResult:
        packet = evidence_packet_from_context(context)
        packet_items = packet_items_for_agent(packet, self.config) if packet is not None else []
        if packet_items:
            citations = dedupe_citations([item.citation for item in packet_items if item.citation is not None])
            source_path = build_packet_source_path(packet, packet_items)
            summary = self.summarizer.summarize(
                agent_name=self.name,
                instructions=(
                    f"{self.config.focus} Prefer the live web evidence when it is available and current. "
                    "Use API/local evidence to verify, quantify, or add historical context."
                ),
                evidence=format_packet_evidence(packet_items, source_path),
            )
            return AgentResult(
                agent_name=self.name,
                summary=summary,
                claims=build_packet_claims(self.name, packet_items, source_path),
                citations=citations,
                confidence=confidence_for_packet(packet_items, citations),
                risks=build_packet_risks(self.config.focus, packet, packet_items),
                follow_up_questions=build_follow_ups(self.config.focus),
            )

        article_query = self.article_query(context)
        observation_query = self.observation_query(context)
        articles = self.repository.latest_articles(article_query)
        observations = (
            self.repository.economic_observations(observation_query)
            if self.config.series_ids
            else []
        )
        citations = build_citations(articles, observations)
        fallback = build_source_fallback_summary(
            context=context,
            articles=articles,
            observations=observations,
            health=self.repository.source_health(list(self.config.expected_source_ids)),
        )

        if not articles and not observations:
            return missing_data_result(self.name, self.config.focus, fallback)

        summary = self.summarizer.summarize(
            agent_name=self.name,
            instructions=self.config.focus,
            evidence=format_evidence(articles, observations, fallback),
        )

        return AgentResult(
            agent_name=self.name,
            summary=summary,
            claims=build_claims(self.name, articles, observations, fallback),
            citations=citations,
            confidence=confidence_for_evidence(len(citations)),
            risks=build_risks(self.config.focus, citations, fallback),
            follow_up_questions=build_follow_ups(self.config.focus),
        )

    def article_query(self, context: AgentContext) -> EvidenceQuery:
        return EvidenceQuery(
            domains=list(context.domains or self.config.domains),
            source_ids=context.source_ids,
            tickers=context.tickers,
            companies=context.companies,
            regions=context.regions,
            time_window=context.time_window or self.config.default_time_window,
            limit=self.config.article_limit,
        )

    def observation_query(self, context: AgentContext) -> EvidenceQuery:
        return EvidenceQuery(
            source_ids=context.source_ids,
            regions=context.regions,
            series_ids=list(self.config.series_ids),
            time_window=context.time_window or self.config.default_time_window,
            limit=self.config.observation_limit,
        )


class NewsDigestAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="NewsDigestAgent",
        focus="Summarize broad world, policy, market, technology, banking, labor, and legal news signals.",
        domains=(
            "World and Geopolitics",
            "U.S. Economy and Policy",
            "Markets and Rates",
            "Technology and AI",
            "Banking and Credit",
            "Consumer and Labor",
            "Regulation and Legal",
        ),
        default_time_window="week",
        expected_source_ids=("bbc-news-rss", "newsapi", "gdelt-cloud", "alpha-vantage"),
    )


class CompanyAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="CompanyAgent",
        focus="Analyze company and ticker-specific news, filings, risks, and catalysts.",
        domains=("Companies and Earnings", "Regulation and Legal", "Technology and AI"),
        default_time_window="month",
        expected_source_ids=("sec-data-apis", "sec-edgar-rss", "finnhub", "alpha-vantage", "newsapi"),
    )


class MarketAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="MarketAgent",
        focus="Analyze market, rates, credit, sector, and broad risk signals without giving direct trading advice.",
        domains=("Markets and Rates", "Banking and Credit", "Commodities and Energy"),
        series_ids=("FEDFUNDS", "MORTGAGE30US", "UNRATE", "FREDDIE_PMMS:*", "ALPHA_VANTAGE:QUOTE:*", "FINNHUB:QUOTE:*"),
        default_time_window="month",
        expected_source_ids=("fred-api", "freddie-mac-pmms", "alpha-vantage", "finnhub", "newsapi"),
    )


class MacroAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="MacroAgent",
        focus="Analyze macroeconomic, policy, inflation, labor, rates, and credit conditions.",
        domains=("U.S. Economy and Policy", "Markets and Rates", "Consumer and Labor"),
        series_ids=("FEDFUNDS", "UNRATE"),
        default_time_window="quarter",
        expected_source_ids=("fred-api", "census-economic-indicators", "alpha-vantage"),
    )


class HousingAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="HousingAgent",
        focus=(
            "Analyze housing, mortgage-rate, real estate, construction, and affordability signals. "
            "When a user asks about a city or state, distinguish local house-price data from national "
            "mortgage-rate context and state when local mortgage-rate data is not available."
        ),
        domains=("Housing and Real Estate", "Markets and Rates", "U.S. Economy and Policy"),
        series_ids=("MORTGAGE30US", "FREDDIE_PMMS:*", "FHFA_HPI:*", "CENSUS_EITS:MHS:*", "CENSUS_EITS:RESSALES:*"),
        default_time_window="quarter",
        observation_limit=10,
        expected_source_ids=("fhfa-hpi", "freddie-mac-pmms", "fred-api", "census-economic-indicators", "newsapi"),
    )


def build_domain_agents(
    repository: ResearchEvidenceRepository,
    summarizer: ResearchSummarizer | None = None,
) -> list[EvidenceBackedDomainAgent]:
    return [
        NewsDigestAgent(repository, summarizer),
        CompanyAgent(repository, summarizer),
        MarketAgent(repository, summarizer),
        MacroAgent(repository, summarizer),
        HousingAgent(repository, summarizer),
    ]


def build_citations(
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
) -> list[AgentCitation]:
    citations: list[AgentCitation] = []
    for article in articles:
        citations.append(
            AgentCitation(
                source_id=article.source_id,
                title=article.citation.title,
                url=article.citation.url,
                publisher=article.publisher or article.source_name,
                published_at=article.published_at,
                retrieved_at=article.retrieved_at,
                supports_claim=article.citation.supports_claim,
            )
        )

    for observation in observations:
        citations.append(
            AgentCitation(
                source_id=observation.source_id,
                title=observation.citation.title,
                publisher=observation.source_name,
                published_at=observation.released_at,
                retrieved_at=observation.retrieved_at,
                supports_claim=observation.citation.supports_claim,
            )
        )

    return citations


def evidence_packet_from_context(context: AgentContext) -> EvidencePacket | None:
    if context.evidence_packet is None:
        return None
    return EvidencePacket.model_validate(context.evidence_packet)


def packet_items_for_agent(
    packet: EvidencePacket | None,
    config: DomainAgentConfig,
) -> list[EvidencePacketItem]:
    if packet is None:
        return []

    selected: list[EvidencePacketItem] = []
    for item in packet.items:
        if item.source_kind == "live_web":
            selected.append(item)
            continue
        if item.source_id and item.source_id in config.expected_source_ids:
            selected.append(item)
            continue
        if packet_item_matches_domains(item, config.domains):
            selected.append(item)

    return selected[:8]


def packet_item_matches_domains(item: EvidencePacketItem, domains: tuple[str, ...]) -> bool:
    if not domains:
        return True
    metadata_domains = item.metadata.get("domains")
    if not isinstance(metadata_domains, str):
        return False
    normalized_domains = {domain.strip().lower() for domain in metadata_domains.split(",") if domain.strip()}
    return bool(normalized_domains & {domain.lower() for domain in domains})


def format_packet_evidence(items: list[EvidencePacketItem], source_path: str) -> str:
    lines = [f"Fused evidence source path: {source_path}"]
    for item in items:
        date = item.published_at or item.retrieved_at or "unknown date"
        publisher = item.publisher or item.source_name or item.source_id or item.source_kind
        scope = f", scope: {item.scope}" if item.scope else ""
        lines.append(
            f"- {item.source_kind} {item.source_quality}: {item.title} "
            f"({publisher}, {date}{scope}) - {item.summary}"
        )
    return "\n".join(lines)


def build_packet_source_path(packet: EvidencePacket, items: list[EvidencePacketItem]) -> str:
    channels = compact_list([item.source_kind for item in items])
    sources = compact_list([item.source_id or item.source_name or item.source_kind for item in items])
    live_statuses = [status for status in packet.retrieval_statuses if status.channel == "live_web"]
    if any(status.status == "success" for status in live_statuses):
        live_note = "live web search succeeded"
    elif live_statuses:
        live_note = f"live web search {live_statuses[0].status}: {live_statuses[0].message}"
    else:
        live_note = "live web search was not requested"
    return f"used fused ranked evidence from {channels}; sources included {sources}; {live_note}."


def build_packet_claims(agent_name: str, items: list[EvidencePacketItem], source_path: str) -> list[AgentClaim]:
    source_ids = dedupe_strings([item.source_id for item in items if item.source_id])
    live_count = sum(1 for item in items if item.source_kind == "live_web")
    supporting_count = len(items) - live_count
    return [
        AgentClaim(
            claim=f"{agent_name} reviewed {len(items)} ranked evidence items, including {live_count} live web items.",
            claim_type="fact",
            source_ids=source_ids,
            confidence="medium" if items else "low",
        ),
        AgentClaim(
            claim=f"{agent_name} source path: {source_path}",
            claim_type="fact",
            source_ids=source_ids,
            confidence="medium" if live_count or supporting_count >= 2 else "low",
        ),
    ]


def build_packet_risks(
    focus: str,
    packet: EvidencePacket,
    items: list[EvidencePacketItem],
) -> list[str]:
    risks = ["This is research context only, not a recommendation to buy, sell, or hold any security."]
    if not any(item.source_kind == "live_web" for item in items):
        risks.append("Live web evidence was not available for this specialist; answer relies on supporting stored data.")
    if len(items) < 3:
        risks.append(f"Evidence coverage is limited for this request: {focus}")
    failed_statuses = [
        status
        for status in packet.retrieval_statuses
        if status.status == "failed" or (status.channel == "live_web" and status.status == "skipped")
    ]
    risks.extend(f"{status.channel} retrieval {status.status}: {status.message}" for status in failed_statuses[:2])
    return dedupe_strings(risks)


def confidence_for_packet(items: list[EvidencePacketItem], citations: list[AgentCitation]) -> ConfidenceLevel:
    live_count = sum(1 for item in items if item.source_kind == "live_web")
    primary_or_reputable = sum(1 for item in items if item.source_quality in {"primary", "reputable"})
    if live_count >= 2 and primary_or_reputable >= 3 and len(citations) >= 3:
        return "high"
    if live_count >= 1 or len(citations) >= 2:
        return "medium"
    return "low"


def dedupe_citations(citations: list[AgentCitation]) -> list[AgentCitation]:
    seen: set[tuple[str | None, str, str | None]] = set()
    deduped: list[AgentCitation] = []
    for citation in citations:
        key = (citation.source_id, citation.title, citation.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(citation)
    return deduped


def build_claims(
    agent_name: str,
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
    fallback: str,
) -> list[AgentClaim]:
    claims: list[AgentClaim] = []
    if articles:
        claims.append(
            AgentClaim(
                claim=f"{agent_name} found {len(articles)} relevant article records.",
                claim_type="fact",
                source_ids=[article.source_id for article in articles],
                confidence="medium",
            )
        )

    if observations:
        claims.append(
            AgentClaim(
                claim=f"{agent_name} found {len(observations)} relevant economic observations.",
                claim_type="fact",
                source_ids=[observation.source_id for observation in observations],
                confidence="medium",
            )
        )

    claims.append(
        AgentClaim(
            claim=f"{agent_name} source path: {fallback}",
            claim_type="fact",
            source_ids=dedupe_strings(
                [article.source_id for article in articles] + [observation.source_id for observation in observations]
            ),
            confidence="medium" if articles or observations else "low",
        )
    )

    return claims


def format_evidence(
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
    fallback: str,
) -> str:
    lines: list[str] = [f"Source fallback summary: {fallback}"]
    for article in articles:
        date = article.published_at or article.retrieved_at or "unknown date"
        detail = article.summary or article.excerpt or "No summary available."
        lines.append(f"- Article: {article.title} ({article.source_name}, {date}) - {detail}")

    for observation in observations:
        date = observation.released_at or observation.retrieved_at or "unknown date"
        unit = f" {observation.unit}" if observation.unit else ""
        region = f" for {observation.region}" if observation.region else ""
        lines.append(
            f"- Economic observation: {observation.display_name} ({observation.series_id}) "
            f"{observation.period}{region} = {observation.value}{unit} ({observation.source_name}, {date}) - "
            f"{observation.description}"
        )

    return "\n".join(lines)


def missing_data_result(agent_name: str, focus: str, fallback: str) -> AgentResult:
    return AgentResult(
        agent_name=agent_name,
        summary=(
            f"{agent_name} did not find enough current ingested evidence for this request. "
            f"{fallback}"
        ),
        claims=[
            AgentClaim(
                claim=f"{agent_name} source path: {fallback}",
                claim_type="fact",
                confidence="low",
            )
        ],
        confidence="low",
        risks=[f"Available ingested data is too thin for {focus.lower()}", fallback],
        follow_up_questions=["Should the app run ingestion again or broaden the time window?"],
    )


def confidence_for_evidence(citation_count: int) -> ConfidenceLevel:
    if citation_count >= 4:
        return "high"
    if citation_count >= 2:
        return "medium"
    return "low"


def build_risks(focus: str, citations: list[AgentCitation], fallback: str) -> list[str]:
    risks = ["This is research context only, not a recommendation to buy, sell, or hold any security."]
    if len(citations) < 2:
        risks.append(f"Evidence coverage is limited for this request: {focus}")
    risks.append(fallback)
    return risks


def build_follow_ups(focus: str) -> list[str]:
    return [
        f"Should the next pass narrow the analysis around {focus.lower()}?",
        "Should the app compare this with older ingested data?",
    ]


def build_source_fallback_summary(
    *,
    context: AgentContext,
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
    health: list[SourceHealthEvidence],
) -> str:
    evidence_count = len(articles) + len(observations)
    local_path = "used local stored evidence" if evidence_count else "checked local stored evidence but found no matching records"
    found_sources = dedupe_strings([article.source_id for article in articles] + [observation.source_id for observation in observations])
    stale_sources = [item.source_id for item in health if item.status == "stale"]
    failed_sources = [item.source_id for item in health if item.status == "failed"]
    skipped_sources = [item.source_id for item in health if item.status == "skipped"]
    unchecked_sources = [item.source_id for item in health if item.status in {"not_configured", "unknown"}]
    fresh_sources = [item.source_id for item in health if item.status == "fresh"]

    notes = [f"Source path: {local_path}."]
    if found_sources:
        notes.append(f"Evidence came from {compact_list(found_sources)}.")
    elif fresh_sources:
        notes.append(f"Fresh sources checked: {compact_list(fresh_sources)}.")

    gaps = []
    if stale_sources:
        gaps.append(f"stale: {compact_list(stale_sources)}")
    if failed_sources:
        gaps.append(f"failed: {compact_list(failed_sources)}")
    if skipped_sources:
        gaps.append(f"skipped: {compact_list(skipped_sources)}")
    if unchecked_sources:
        gaps.append(f"not checked/configured: {compact_list(unchecked_sources)}")
    if gaps:
        notes.append(f"Coverage gaps: {'; '.join(gaps)}.")

    if context.regions and includes_local_region(context.regions) and uses_national_only_observations(observations):
        notes.append(
            "Regional note: available mortgage-rate evidence is national; local mortgage-rate data was not found."
        )

    return " ".join(notes)


def includes_local_region(regions: list[str]) -> bool:
    normalized_national = {"us", "usa", "united states", "us market"}
    return any(region.strip().lower() not in normalized_national for region in regions)


def uses_national_only_observations(observations: list[EconomicObservationEvidence]) -> bool:
    if not observations:
        return False
    mortgage_observations = [
        observation
        for observation in observations
        if "mortgage" in observation.display_name.lower() or observation.series_id.startswith(("MORTGAGE", "FREDDIE_PMMS"))
    ]
    if not mortgage_observations:
        return False
    return all((observation.region or "").strip().lower() in {"us", "usa", "united states"} for observation in mortgage_observations)


def compact_list(values: list[str], *, limit: int = 4) -> str:
    unique = dedupe_strings(values)
    if len(unique) <= limit:
        return ", ".join(unique)
    return f"{', '.join(unique[:limit])}, and {len(unique) - limit} more"


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped
