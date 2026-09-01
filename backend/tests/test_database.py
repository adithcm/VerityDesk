import os
import sqlite3
import subprocess
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Article, Citation, Report, Source
from app.db.session import create_database_engine


EXPECTED_TABLES = {
    "agent_runs",
    "articles",
    "citations",
    "companies",
    "economic_observations",
    "reports",
    "sources",
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
