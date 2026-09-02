from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Article, ExternalID, IngestionRun, RetrievedSnapshot, SourceHealth
from app.services import rss_ingestion
from app.services.rss_ingestion import (
    FetchedFeed,
    RSSFeedConfig,
    ingest_rss_feed,
    parse_feed_entries,
)


BBC_RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>BBC News</title>
    <item>
      <title>Markets rise as investors assess rates</title>
      <link>https://www.bbc.com/news/business-1#fragment</link>
      <guid>bbc-business-1</guid>
      <pubDate>Wed, 02 Sep 2026 14:30:00 GMT</pubDate>
      <description>Global markets moved higher after fresh rate comments.</description>
    </item>
  </channel>
</rss>
"""


SEC_ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Latest EDGAR Filings</title>
  <entry>
    <title>10-K - Example Company</title>
    <link rel="alternate" href="https://www.sec.gov/Archives/example/" />
    <id>urn:sec:accession-number:0000320193-26-000001</id>
    <updated>2026-09-02T15:45:00Z</updated>
    <summary>Example Company filed a 10-K.</summary>
    <author><name>SEC</name></author>
  </entry>
</feed>
"""


def build_config(source_key: str = "bbc-news-rss") -> RSSFeedConfig:
    return RSSFeedConfig(
        source_key=source_key,
        feed_url="https://feeds.example.test/rss.xml",
        source_name="BBC News RSS",
        domains=("World and Geopolitics", "Markets and Rates"),
        publisher="BBC News RSS",
        storage_policy="metadata_and_excerpt",
        source_type="official_rss",
        access_method="rss",
        update_cadence="daily",
        reliability_tier="standard",
        enabled=True,
        base_url="https://www.bbc.com/news",
    )


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_parse_rss_feed_entries_normalizes_metadata() -> None:
    retrieved_at = datetime(2026, 9, 2, 16, 0, tzinfo=UTC)

    entries = parse_feed_entries(build_config(), BBC_RSS_SAMPLE, retrieved_at)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "Markets rise as investors assess rates"
    assert entry.url == "https://www.bbc.com/news/business-1#fragment"
    assert entry.canonical_url == "https://www.bbc.com/news/business-1"
    assert entry.external_id == "bbc-business-1"
    assert entry.publisher == "BBC News RSS"
    assert entry.published_at == datetime(2026, 9, 2, 14, 30, tzinfo=UTC)
    assert entry.retrieved_at == retrieved_at
    assert entry.excerpt == "Global markets moved higher after fresh rate comments."
    assert entry.content_hash


def test_parse_atom_feed_entries_normalizes_sec_metadata() -> None:
    config = build_config(source_key="sec-edgar-rss")

    entries = parse_feed_entries(config, SEC_ATOM_SAMPLE, datetime(2026, 9, 2, 16, 0, tzinfo=UTC))

    assert len(entries) == 1
    entry = entries[0]
    assert entry.title == "10-K - Example Company"
    assert entry.url == "https://www.sec.gov/Archives/example/"
    assert entry.canonical_url == "https://www.sec.gov/Archives/example"
    assert entry.external_id == "urn:sec:accession-number:0000320193-26-000001"
    assert entry.author == "SEC"
    assert entry.summary == "Example Company filed a 10-K."


def test_ingest_rss_feed_persists_article_snapshot_run_and_health(monkeypatch) -> None:
    retrieved_at = datetime(2026, 9, 2, 16, 0, tzinfo=UTC)

    def fake_fetch(config: RSSFeedConfig) -> FetchedFeed:
        return FetchedFeed(
            url=config.feed_url,
            body=BBC_RSS_SAMPLE,
            response_headers={"content-type": "application/rss+xml"},
            retrieved_at=retrieved_at,
        )

    monkeypatch.setattr(rss_ingestion, "fetch_rss_feed", fake_fetch)

    with build_session() as session:
        result = ingest_rss_feed(session, build_config())

        article = session.scalar(select(Article))
        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))
        snapshot = session.scalar(select(RetrievedSnapshot))
        external_id = session.scalar(select(ExternalID))

        assert result.status == "success"
        assert result.items_seen == 1
        assert result.items_inserted == 1
        assert result.items_updated == 0
        assert article is not None
        assert article.title == "Markets rise as investors assess rates"
        assert run is not None
        assert run.status == "success"
        assert run.items_inserted == 1
        assert health is not None
        assert health.status == "fresh"
        assert health.latest_item_title == article.title
        assert snapshot is not None
        assert snapshot.article_id == article.id
        assert external_id is not None
        assert external_id.article_id == article.id


def test_ingest_rss_feed_deduplicates_existing_external_id(monkeypatch) -> None:
    retrieved_at = datetime(2026, 9, 2, 16, 0, tzinfo=UTC)

    def fake_fetch(config: RSSFeedConfig) -> FetchedFeed:
        return FetchedFeed(
            url=config.feed_url,
            body=BBC_RSS_SAMPLE,
            response_headers={},
            retrieved_at=retrieved_at,
        )

    monkeypatch.setattr(rss_ingestion, "fetch_rss_feed", fake_fetch)

    with build_session() as session:
        first_result = ingest_rss_feed(session, build_config())
        second_result = ingest_rss_feed(session, build_config())

        articles = session.scalars(select(Article)).all()
        snapshots = session.scalars(select(RetrievedSnapshot)).all()
        runs = session.scalars(select(IngestionRun)).all()

        assert first_result.items_inserted == 1
        assert second_result.items_inserted == 0
        assert second_result.items_updated == 1
        assert len(articles) == 1
        assert len(snapshots) == 2
        assert len(runs) == 2


def test_ingest_rss_feed_logs_failure_and_health(monkeypatch) -> None:
    def fake_fetch(config: RSSFeedConfig) -> FetchedFeed:
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(rss_ingestion, "fetch_rss_feed", fake_fetch)

    with build_session() as session:
        result = ingest_rss_feed(session, build_config())

        run = session.scalar(select(IngestionRun))
        health = session.scalar(select(SourceHealth))

        assert result.status == "failed"
        assert result.error == "network unavailable"
        assert run is not None
        assert run.status == "failed"
        assert run.error == "network unavailable"
        assert health is not None
        assert health.status == "failed"
        assert health.consecutive_failures == 1
        assert health.last_error == "network unavailable"
