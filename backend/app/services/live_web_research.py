import json
import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

import certifi

from app.core.config import Settings, get_settings
from app.schemas.live_web import (
    LiveWebCitation,
    LiveWebEvidence,
    LiveWebSearchRequest,
    LiveWebSearchResponse,
    SourceQuality,
)


TAVILY_SEARCH_URL = "https://api.tavily.com/search"

PRIMARY_DOMAINS = {
    "bea.gov",
    "bls.gov",
    "census.gov",
    "data.sec.gov",
    "federalreserve.gov",
    "fhfa.gov",
    "fred.stlouisfed.org",
    "sec.gov",
    "treasury.gov",
}

REPUTABLE_DOMAINS = {
    "apnews.com",
    "bbc.com",
    "bloomberg.com",
    "cnbc.com",
    "finance.yahoo.com",
    "ft.com",
    "marketwatch.com",
    "morningstar.com",
    "reuters.com",
    "wsj.com",
}

PROVIDER_DOMAINS = {
    "alphavantage.co",
    "finnhub.io",
    "freddiemac.com",
    "newsapi.org",
}

BLOCKED_DOMAINS = {
    "pinterest.com",
    "reddit.com",
    "tiktok.com",
    "x.com",
}


@dataclass(frozen=True)
class TavilySearchResult:
    title: str
    url: str
    content: str
    score: float = 0
    published_date: str | None = None


def run_live_web_search(
    request: LiveWebSearchRequest,
    *,
    settings: Settings | None = None,
) -> LiveWebSearchResponse:
    settings = settings or get_settings()
    if request.provider != "tavily":
        return LiveWebSearchResponse(
            provider=request.provider,
            status="failed",
            query=request.query,
            message=f"Unsupported live web provider: {request.provider}",
        )

    if not settings.tavily_api_key:
        return LiveWebSearchResponse(
            provider=request.provider,
            status="skipped",
            query=request.query,
            message="Missing required API key setting: TAVILY_API_KEY",
        )

    try:
        payload = fetch_tavily_search(request, settings)
        results = tavily_payload_to_evidence(payload, request)
    except Exception as error:
        return LiveWebSearchResponse(
            provider=request.provider,
            status="failed",
            query=request.query,
            message=str(error),
        )

    return LiveWebSearchResponse(
        provider=request.provider,
        status="success",
        query=request.query,
        results=results,
        message=f"Retrieved {len(results)} citation-ready live web results.",
    )


def fetch_tavily_search(request: LiveWebSearchRequest, settings: Settings) -> dict:
    body = {
        "query": request.query,
        "max_results": request.max_results,
        "search_depth": "advanced",
        "include_answer": False,
        "include_raw_content": False,
        "include_domains": request.include_domains,
        "exclude_domains": sorted({*request.exclude_domains, *BLOCKED_DOMAINS}),
    }
    http_request = Request(
        TAVILY_SEARCH_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.tavily_api_key}",
            "Content-Type": "application/json",
            "User-Agent": settings.investoragent_user_agent,
        },
        method="POST",
    )
    context = ssl.create_default_context(cafile=certifi.where())

    try:
        with urlopen(http_request, timeout=30, context=context) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")[:500]
        raise ValueError(f"Tavily search failed with HTTP {error.code}: {message}") from error
    except URLError as error:
        raise ValueError(f"Unable to reach Tavily search: {error.reason}") from error
    except json.JSONDecodeError as error:
        raise ValueError("Tavily search returned a non-JSON response.") from error


def tavily_payload_to_evidence(payload: dict, request: LiveWebSearchRequest) -> list[LiveWebEvidence]:
    retrieved_at = datetime.now(UTC).isoformat()
    results = payload.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Tavily search returned malformed results.")

    evidence: list[LiveWebEvidence] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        result = parse_tavily_result(item)
        if result is None or should_block_result(result.url, request):
            continue
        quality = classify_source_quality(result.url)
        excerpt = result.content.strip()
        if not excerpt:
            continue
        evidence.append(
            LiveWebEvidence(
                title=result.title,
                url=result.url,
                publisher=publisher_from_url(result.url),
                published_at=result.published_date,
                retrieved_at=retrieved_at,
                excerpt=excerpt,
                source_quality=quality,
                relevance_score=result.score,
                citation=LiveWebCitation(
                    title=result.title,
                    url=result.url,
                    publisher=publisher_from_url(result.url),
                    published_at=result.published_date,
                    retrieved_at=retrieved_at,
                    supports_claim=build_support_claim(result, quality),
                    source_quality=quality,
                ),
            )
        )

    return sorted(evidence, key=lambda result: quality_sort_key(result), reverse=True)[: request.max_results]


def parse_tavily_result(item: dict) -> TavilySearchResult | None:
    title = optional_text(item.get("title"))
    url = optional_text(item.get("url"))
    content = optional_text(item.get("content"))
    if not title or not url or not content:
        return None
    return TavilySearchResult(
        title=title,
        url=url,
        content=content,
        score=parse_float(item.get("score")) or 0,
        published_date=optional_text(item.get("published_date")),
    )


def should_block_result(url: str, request: LiveWebSearchRequest) -> bool:
    domain = root_domain(url)
    include_domains = {normalize_domain(value) for value in request.include_domains}
    exclude_domains = {normalize_domain(value) for value in request.exclude_domains}
    return bool(
        domain in BLOCKED_DOMAINS
        or domain in exclude_domains
        or (include_domains and domain not in include_domains)
    )


def classify_source_quality(url: str) -> SourceQuality:
    domain = root_domain(url)
    if domain in PRIMARY_DOMAINS or domain.endswith(".gov"):
        return "primary"
    if domain in REPUTABLE_DOMAINS:
        return "reputable"
    if domain in PROVIDER_DOMAINS:
        return "provider"
    return "discovery"


def build_support_claim(result: TavilySearchResult, quality: SourceQuality) -> str:
    return f"Live web {quality} source result retrieved for: {result.title}"


def quality_sort_key(result: LiveWebEvidence) -> tuple[int, float]:
    quality_rank = {"primary": 4, "reputable": 3, "provider": 2, "discovery": 1}
    return (quality_rank[result.source_quality], result.relevance_score)


def publisher_from_url(url: str) -> str | None:
    return root_domain(url) or None


def root_domain(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def normalize_domain(value: str) -> str:
    text = value.strip().lower()
    if text.startswith("http"):
        return root_domain(text)
    return text[4:] if text.startswith("www.") else text


def optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
