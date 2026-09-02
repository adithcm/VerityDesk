import os
import sqlite3
import subprocess
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    Article,
    Citation,
    ExternalID,
    IngestionRun,
    Report,
    RetrievedSnapshot,
    Source,
    SourceHealth,
)
from app.db.session import create_database_engine


EXPECTED_TABLES = {
    "agent_runs",
    "articles",
    "citations",
    "companies",
    "economic_observations",
    "external_ids",
    "ingestion_runs",
    "reports",
    "retrieved_snapshots",
    "sources",
    "source_health",
    "user_settings",
}


def test_model_metadata_has_expected_tables() -> None:
    assert EXPECTED_TABLES.issubset(Base.metadata.tables.keys())


def test_create_database_engine_uses_sqlite_connect_args() -> None:
    engine = create_database_engine("sqlite:///:memory:")

    assert engine.url.database == ":memory:"


def test_create_database_engine_creates_parent_directory(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "investoragent.db"

    create_database_engine(f"sqlite:///{database_path}")

    assert database_path.parent.exists()


def test_models_can_be_inserted_with_relationships() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
        source = Source(
            name="BBC News RSS",
            base_url="https://www.bbc.com/news",
            source_type="official_rss",
            domains=["World and Geopolitics"],
            access_method="rss",
        )
        article = Article(
            source=source,
            title="Markets react to global news",
            url="https://example.com/story",
            domains=["Markets and Rates"],
        )
        report = Report(
            report_type="daily_briefing",
            title="Daily Briefing",
            body="Research summary.",
            domains=["Markets and Rates"],
        )
        citation = Citation(
            report=report,
            article=article,
            source=source,
            url=article.url,
            title=article.title,
            supports_claim="Markets reacted to global news.",
        )

        session.add(citation)
        session.commit()

        assert source.id is not None
        assert article.id is not None
        assert report.id is not None
        assert citation.id is not None
        assert article.source.name == "BBC News RSS"
        assert report.citations[0].source.name == "BBC News RSS"


def test_ingestion_models_can_track_runs_health_and_snapshots() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
        source = Source(
            name="SEC EDGAR RSS",
            base_url="https://www.sec.gov",
            source_type="official_rss",
            domains=["Companies and Earnings", "Regulation and Legal"],
            access_method="rss",
        )
        article = Article(
            source=source,
            title="Company files annual report",
            url="https://www.sec.gov/example-filing",
            domains=["Companies and Earnings"],
            tickers=["AAPL"],
            content_hash="hash-1",
            storage_policy="metadata_and_excerpt",
        )
        run = IngestionRun(
            source=source,
            source_key="sec-edgar-rss",
            run_type="manual",
            status="success",
            items_seen=1,
            items_inserted=1,
            run_metadata={"connector": "rss"},
        )
        health = SourceHealth(
            source_id=None,
            source_key="sec-edgar-rss",
            status="fresh",
            latest_item_title=article.title,
            freshness_window_hours=24,
        )
        snapshot = RetrievedSnapshot(
            source=source,
            article=article,
            source_key="sec-edgar-rss",
            url=article.url,
            content_hash="hash-1",
            storage_policy="metadata_and_excerpt",
            excerpt="Short excerpt only.",
            response_headers={"content-type": "application/rss+xml"},
        )
        external_id = ExternalID(
            source_key="sec-edgar-rss",
            external_id="0000320193-26-000001",
            entity_type="article",
            article=article,
            id_metadata={"form": "10-K"},
        )

        session.add_all([run, health, snapshot, external_id])
        session.commit()

        assert run.id is not None
        assert health.id is not None
        assert snapshot.id is not None
        assert external_id.id is not None
        assert source.ingestion_runs[0].items_inserted == 1
        assert article.snapshots[0].excerpt == "Short excerpt only."
        assert article.external_ids[0].external_id == "0000320193-26-000001"


def test_alembic_initial_migration_creates_expected_tables(tmp_path: Path) -> None:
    database_path = tmp_path / "investoragent.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{database_path}"

    result = subprocess.run(
        ["../.venv/bin/alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            ).fetchall()
        }

    assert EXPECTED_TABLES.issubset(table_names)
