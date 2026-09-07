from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.utils import ensure_database_parent_dir


def create_database_engine(database_url: str | None = None) -> Engine:
    settings = get_settings()
    url = database_url or settings.database_url
    ensure_database_parent_dir(url)
    connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}

    database_engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):
        configure_sqlite_connection(database_engine)

    return database_engine


def configure_sqlite_connection(database_engine: Engine) -> None:
    @event.listens_for(database_engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
