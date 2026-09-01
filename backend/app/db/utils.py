from pathlib import Path

from sqlalchemy.engine import make_url


def ensure_database_parent_dir(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return

    database = url.database
    if not database or database == ":memory:":
        return

    Path(database).parent.mkdir(parents=True, exist_ok=True)
