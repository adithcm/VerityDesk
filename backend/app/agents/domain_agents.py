from __future__ import annotations

from dataclasses import dataclass

from app.agents.model_client import ResearchSummarizer, TemplateResearchSummarizer
from app.schemas.agent import AgentCitation, AgentClaim, AgentContext, AgentResult, ConfidenceLevel
from app.services.research_evidence import (
    ArticleEvidence,
    EconomicObservationEvidence,
    EvidenceQuery,
    ResearchEvidenceRepository,
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
        articles = self.repository.latest_articles(self.article_query(context))
        observations = (
            self.repository.economic_observations(self.observation_query(context))
            if self.config.series_ids
            else []
        )
        citations = build_citations(articles, observations)

        if not articles and not observations:
            return missing_data_result(self.name, self.config.focus)

        summary = self.summarizer.summarize(
            agent_name=self.name,
            instructions=self.config.focus,
            evidence=format_evidence(articles, observations),
        )

        return AgentResult(
            agent_name=self.name,
            summary=summary,
            claims=build_claims(self.name, articles, observations),
            citations=citations,
            confidence=confidence_for_evidence(len(citations)),
            risks=build_risks(self.config.focus, citations),
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
    )


class CompanyAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="CompanyAgent",
        focus="Analyze company and ticker-specific news, filings, risks, and catalysts.",
        domains=("Companies and Earnings", "Regulation and Legal", "Technology and AI"),
        default_time_window="month",
    )


class MarketAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="MarketAgent",
        focus="Analyze market, rates, credit, sector, and broad risk signals without giving direct trading advice.",
        domains=("Markets and Rates", "Banking and Credit", "Commodities and Energy"),
        series_ids=("FEDFUNDS", "MORTGAGE30US", "UNRATE"),
        default_time_window="month",
    )


class MacroAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="MacroAgent",
        focus="Analyze macroeconomic, policy, inflation, labor, rates, and credit conditions.",
        domains=("U.S. Economy and Policy", "Markets and Rates", "Consumer and Labor"),
        series_ids=("FEDFUNDS", "UNRATE"),
        default_time_window="quarter",
    )


class HousingAgent(EvidenceBackedDomainAgent):
    config = DomainAgentConfig(
        name="HousingAgent",
        focus="Analyze housing, mortgage-rate, real estate, construction, and affordability signals.",
        domains=("Housing and Real Estate", "Markets and Rates", "U.S. Economy and Policy"),
        series_ids=("MORTGAGE30US",),
        default_time_window="quarter",
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


def build_claims(
    agent_name: str,
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
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

    return claims


def format_evidence(
    articles: list[ArticleEvidence],
    observations: list[EconomicObservationEvidence],
) -> str:
    lines: list[str] = []
    for article in articles:
        date = article.published_at or article.retrieved_at or "unknown date"
        detail = article.summary or article.excerpt or "No summary available."
        lines.append(f"- Article: {article.title} ({article.source_name}, {date}) - {detail}")

    for observation in observations:
        date = observation.released_at or observation.retrieved_at or "unknown date"
        unit = f" {observation.unit}" if observation.unit else ""
        lines.append(
            f"- Economic observation: {observation.display_name} ({observation.series_id}) "
            f"{observation.period} = {observation.value}{unit} ({observation.source_name}, {date}) - "
            f"{observation.description}"
        )

    return "\n".join(lines)


def missing_data_result(agent_name: str, focus: str) -> AgentResult:
    return AgentResult(
        agent_name=agent_name,
        summary=f"{agent_name} did not find enough current ingested evidence for this request.",
        confidence="low",
        risks=[f"Available ingested data is too thin for {focus.lower()}"],
        follow_up_questions=["Should the app run ingestion again or broaden the time window?"],
    )


def confidence_for_evidence(citation_count: int) -> ConfidenceLevel:
    if citation_count >= 4:
        return "high"
    if citation_count >= 2:
        return "medium"
    return "low"


def build_risks(focus: str, citations: list[AgentCitation]) -> list[str]:
    risks = ["This is research context only, not a recommendation to buy, sell, or hold any security."]
    if len(citations) < 2:
        risks.append(f"Evidence coverage is limited for this request: {focus}")
    return risks


def build_follow_ups(focus: str) -> list[str]:
    return [
        f"Should the next pass narrow the analysis around {focus.lower()}?",
        "Should the app compare this with older ingested data?",
    ]
