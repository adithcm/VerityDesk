from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
import ssl
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import certifi
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Article, ExternalID, IngestionRun, RetrievedSnapshot, Source, SourceHealth
from app.schemas.source import SourceCatalogEntry
from app.services.source_catalog import load_source_catalog


RSS_FEED_URLS: dict[str, str] = {
    "bbc-news-rss": "https://feeds.bbci.co.uk/news/rss.xml",
    "sec-edgar-rss": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&output=atom",
}


@dataclass(frozen=True)
class RSSFeedConfig:
    source_key: str
    feed_url: str
    source_name: str
    domains: tuple[str, ...]
    publisher: str | None
    storage_policy: str
    source_type: str
    access_method: str
    update_cadence: str
    reliability_tier: str
    enabled: bool
    base_url: str | None = None


@dataclass(frozen=True)
class NormalizedFeedEntry:
    source_key: str
    title: str
    url: str
    canonical_url: str
    external_id: str | None
    publisher: str | None
    author: str | None
    published_at: datetime | None
    retrieved_at: datetime
    summary: str | None
    excerpt: str | None
    domains: list[str]
    content_hash: str
    storage_policy: str


@dataclass(frozen=True)
class FetchedFeed:
    url: str
    body: bytes
    response_headers: dict[str, str]
    retrieved_at: datetime


@dataclass(frozen=True)
class IngestionResult:
    source_key: str
    status: str
    items_seen: int
    items_inserted: int
    items_updated: int
    items_skipped: int
    error: str | None = None


def get_configured_rss_feeds() -> list[RSSFeedConfig]:
    catalog_by_id = {source.id: source for source in load_source_catalog()}

    feeds: list[RSSFeedConfig] = []
    for source_key, feed_url in RSS_FEED_URLS.items():
        source = catalog_by_id[source_key]
        feeds.append(build_rss_feed_config(source, feed_url))

    return feeds


def build_rss_feed_config(source: SourceCatalogEntry, feed_url: str) -> RSSFeedConfig:
    return RSSFeedConfig(
        source_key=source.id,
        feed_url=feed_url,
        source_name=source.name,
        domains=tuple(source.domains),
        publisher=source.name,
        storage_policy=source.storage_policy,
        source_type=source.source_type,
        access_method=source.access_method,
        update_cadence=source.update_cadence,
        reliability_tier=source.reliability_tier,
        enabled=source.enabled_by_default,
        base_url=source.base_url,
    )


def fetch_rss_feed(config: RSSFeedConfig) -> FetchedFeed:
    settings = get_settings()
    request = Request(
        config.feed_url,
        headers={
            "User-Agent": settings.investoragent_user_agent,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )

    context = ssl.create_default_context(cafile=certifi.where())

    with urlopen(request, timeout=20, context=context) as response:
        return FetchedFeed(
            url=config.feed_url,
            body=response.read(),
            response_headers=dict(response.headers.items()),
            retrieved_at=datetime.now(UTC),
        )


def ingest_configured_rss_feeds(session: Session) -> list[IngestionResult]:
    return [ingest_rss_feed(session, config) for config in get_configured_rss_feeds()]


def ingest_rss_feed(session: Session, config: RSSFeedConfig) -> IngestionResult:
    started_at = datetime.now(UTC)
    run = IngestionRun(
        source_key=config.source_key,
        run_type="manual",
        status="running",
        started_at=started_at,
        run_metadata={"feed_url": config.feed_url},
    )
    session.add(run)
    session.flush()

    try:
        source = get_or_create_source(session, config)
        fetched_feed = fetch_rss_feed(config)
        entries = parse_feed_entries(config, fetched_feed.body, fetched_feed.retrieved_at)

        inserted = 0
        updated = 0
        skipped = 0
        latest_entry: NormalizedFeedEntry | None = None

        run.source = source

        for entry in entries:
            article, was_inserted = upsert_article_from_entry(session, source, entry)
            if article is None:
                skipped += 1
                continue

            if was_inserted:
                inserted += 1
            else:
                updated += 1

            add_retrieved_snapshot(session, source, article, entry, fetched_feed.response_headers)
            latest_entry = get_latest_entry(latest_entry, entry)

        completed_at = datetime.now(UTC)
        run.status = "success"
        run.completed_at = completed_at
        run.items_seen = len(entries)
        run.items_inserted = inserted
        run.items_updated = updated
        run.items_skipped = skipped
        update_source_health_success(session, source, config, started_at, completed_at, latest_entry)
        session.commit()

        return IngestionResult(
            source_key=config.source_key,
            status="success",
            items_seen=len(entries),
            items_inserted=inserted,
            items_updated=updated,
            items_skipped=skipped,
        )
    except Exception as error:
        completed_at = datetime.now(UTC)
        message = str(error)
        run.status = "failed"
        run.completed_at = completed_at
        run.error = message
        update_source_health_failure(session, config, started_at, message)
        session.commit()

        return IngestionResult(
            source_key=config.source_key,
            status="failed",
            items_seen=0,
            items_inserted=0,
            items_updated=0,
            items_skipped=0,
            error=message,
        )


def parse_feed_entries(
    config: RSSFeedConfig,
    feed_body: bytes,
    retrieved_at: datetime | None = None,
) -> list[NormalizedFeedEntry]:
    retrieved = retrieved_at or datetime.now(UTC)
    root = ElementTree.fromstring(feed_body)
    root_name = local_name(root.tag)

    if root_name == "rss":
        items = root.findall("./channel/item")
        return [parse_rss_item(config, item, retrieved) for item in items if item is not None]

    if root_name == "feed":
        entries = [child for child in root if local_name(child.tag) == "entry"]
        return [parse_atom_entry(config, entry, retrieved) for entry in entries if entry is not None]

    raise ValueError(f"Unsupported feed format: {root_name}")


def parse_rss_item(
    config: RSSFeedConfig,
    item: ElementTree.Element,
    retrieved_at: datetime,
) -> NormalizedFeedEntry:
    title = required_text(child_text(item, "title"), "RSS item title")
    link = required_text(child_text(item, "link"), "RSS item link")
    summary = child_text(item, "description")
    external_id = child_text(item, "guid")
    published_at = parse_datetime(child_text(item, "pubDate"))
    author = child_text(item, "author") or child_text(item, "creator")
    canonical_url = canonicalize_url(link)
    content_hash = build_content_hash(title, canonical_url, summary, published_at)

    return NormalizedFeedEntry(
        source_key=config.source_key,
        title=title,
        url=link,
        canonical_url=canonical_url,
        external_id=external_id,
        publisher=config.publisher,
        author=author,
        published_at=published_at,
        retrieved_at=retrieved_at,
        summary=summary,
        excerpt=truncate_text(summary, 1000),
        domains=list(config.domains),
        content_hash=content_hash,
        storage_policy=config.storage_policy,
    )


def parse_atom_entry(
    config: RSSFeedConfig,
    entry: ElementTree.Element,
    retrieved_at: datetime,
) -> NormalizedFeedEntry:
    title = required_text(child_text(entry, "title"), "Atom entry title")
    link = required_text(atom_link(entry), "Atom entry link")
    summary = child_text(entry, "summary") or child_text(entry, "content")
    external_id = child_text(entry, "id")
    published_at = parse_datetime(child_text(entry, "published") or child_text(entry, "updated"))
    author = atom_author(entry)
    canonical_url = canonicalize_url(link)
    content_hash = build_content_hash(title, canonical_url, summary, published_at)

    return NormalizedFeedEntry(
        source_key=config.source_key,
        title=title,
        url=link,
        canonical_url=canonical_url,
        external_id=external_id,
        publisher=config.publisher,
        author=author,
        published_at=published_at,
        retrieved_at=retrieved_at,
        summary=summary,
        excerpt=truncate_text(summary, 1000),
        domains=list(config.domains),
        content_hash=content_hash,
        storage_policy=config.storage_policy,
    )


def get_or_create_source(session: Session, config: RSSFeedConfig) -> Source:
    source = session.scalar(select(Source).where(Source.name == config.source_name))

    if source:
        return source

    source = Source(
        name=config.source_name,
        base_url=config.base_url,
        source_type=config.source_type,
        domains=list(config.domains),
        access_method=config.access_method,
        update_cadence=config.update_cadence,
        reliability_tier=config.reliability_tier,
        enabled=config.enabled,
    )
    session.add(source)
    session.flush()
    return source


def upsert_article_from_entry(
    session: Session,
    source: Source,
    entry: NormalizedFeedEntry,
) -> tuple[Article | None, bool]:
    article = find_existing_article(session, entry)
    was_inserted = article is None

    if article is None:
        article = Article(
            source=source,
            title=entry.title,
            url=entry.url,
            canonical_url=entry.canonical_url,
            publisher=entry.publisher,
            author=entry.author,
            published_at=entry.published_at,
            retrieved_at=entry.retrieved_at,
            summary=entry.summary,
            excerpt=entry.excerpt,
            domains=entry.domains,
            content_hash=entry.content_hash,
            dedupe_group_id=entry.external_id or entry.content_hash,
            storage_policy=entry.storage_policy,
        )
        session.add(article)
        session.flush()
    else:
        article.retrieved_at = entry.retrieved_at
        article.summary = entry.summary or article.summary
        article.excerpt = entry.excerpt or article.excerpt
        article.content_hash = entry.content_hash

    if entry.external_id:
        ensure_external_id(session, article, entry)

    return article, was_inserted


def find_existing_article(session: Session, entry: NormalizedFeedEntry) -> Article | None:
    if entry.external_id:
        existing_external_id = session.scalar(
            select(ExternalID).where(
                ExternalID.source_key == entry.source_key,
                ExternalID.external_id == entry.external_id,
                ExternalID.entity_type == "article",
            )
        )
        if existing_external_id and existing_external_id.article:
            return existing_external_id.article

    return session.scalar(
        select(Article).where(
            (Article.url == entry.url) | (Article.canonical_url == entry.canonical_url)
        )
    )


def ensure_external_id(session: Session, article: Article, entry: NormalizedFeedEntry) -> None:
    existing_external_id = session.scalar(
        select(ExternalID).where(
            ExternalID.source_key == entry.source_key,
            ExternalID.external_id == entry.external_id,
            ExternalID.entity_type == "article",
        )
    )

    if existing_external_id:
        existing_external_id.article = article
        return

    session.add(
        ExternalID(
            source_key=entry.source_key,
            external_id=entry.external_id or "",
            entity_type="article",
            article=article,
            id_metadata={"canonical_url": entry.canonical_url},
        )
    )


def add_retrieved_snapshot(
    session: Session,
    source: Source,
    article: Article,
    entry: NormalizedFeedEntry,
    response_headers: dict[str, str],
) -> None:
    session.add(
        RetrievedSnapshot(
            source=source,
            article=article,
            source_key=entry.source_key,
            url=entry.url,
            retrieved_at=entry.retrieved_at,
            content_hash=entry.content_hash,
            storage_policy=entry.storage_policy,
            excerpt=entry.excerpt,
            response_headers=response_headers,
        )
    )


def update_source_health_success(
    session: Session,
    source: Source,
    config: RSSFeedConfig,
    attempted_at: datetime,
    completed_at: datetime,
    latest_entry: NormalizedFeedEntry | None,
) -> None:
    health = get_or_create_source_health(session, config)
    health.source = source
    health.status = "fresh"
    health.last_attempt_at = attempted_at
    health.last_success_at = completed_at
    health.consecutive_failures = 0
    health.last_error = None
    health.stale_after = completed_at + timedelta(hours=health.freshness_window_hours)

    if latest_entry:
        health.latest_item_published_at = latest_entry.published_at
        health.latest_item_title = latest_entry.title


def update_source_health_failure(
    session: Session,
    config: RSSFeedConfig,
    attempted_at: datetime,
    error: str,
) -> None:
    health = get_or_create_source_health(session, config)
    health.status = "failed"
    health.last_attempt_at = attempted_at
    health.consecutive_failures += 1
    health.last_error = error


def get_or_create_source_health(session: Session, config: RSSFeedConfig) -> SourceHealth:
    health = session.scalar(select(SourceHealth).where(SourceHealth.source_key == config.source_key))

    if health:
        return health

    health = SourceHealth(
        source_key=config.source_key,
        status="not_configured",
        freshness_window_hours=freshness_window_for_cadence(config.update_cadence),
        health_metadata={"feed_url": config.feed_url},
    )
    session.add(health)
    session.flush()
    return health


def get_latest_entry(
    current: NormalizedFeedEntry | None,
    candidate: NormalizedFeedEntry,
) -> NormalizedFeedEntry:
    if current is None:
        return candidate

    if candidate.published_at is None:
        return current

    if current.published_at is None or candidate.published_at > current.published_at:
        return candidate

    return current


def freshness_window_for_cadence(update_cadence: str) -> int:
    if "intraday" in update_cadence:
        return 6
    if "weekly" in update_cadence:
        return 168
    if "monthly" in update_cadence or "quarterly" in update_cadence:
        return 720
    return 24


def child_text(element: ElementTree.Element, child_name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == child_name:
            return normalize_text(child.text)

    return None


def atom_link(entry: ElementTree.Element) -> str | None:
    first_link: str | None = None

    for child in entry:
        if local_name(child.tag) != "link":
            continue

        href = child.attrib.get("href")
        if not href:
            continue

        first_link = first_link or href
        if child.attrib.get("rel", "alternate") == "alternate":
            return href

    return first_link


def atom_author(entry: ElementTree.Element) -> str | None:
    for child in entry:
        if local_name(child.tag) != "author":
            continue

        name = child_text(child, "name")
        if name:
            return name

    return None


def local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)

    return parsed


def canonicalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path.rstrip("/"), parts.query, ""))


def build_content_hash(
    title: str,
    canonical_url: str,
    summary: str | None,
    published_at: datetime | None,
) -> str:
    raw = "|".join([title, canonical_url, summary or "", published_at.isoformat() if published_at else ""])
    return sha256(raw.encode("utf-8")).hexdigest()


def truncate_text(value: str | None, limit: int) -> str | None:
    if value is None or len(value) <= limit:
        return value

    return value[: limit - 3].rstrip() + "..."


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = " ".join(value.split())
    return normalized or None


def required_text(value: str | None, field_name: str) -> str:
    if not value:
        raise ValueError(f"Missing required {field_name}")

    return value
