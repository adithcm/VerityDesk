import json
from dataclasses import asdict

from app.db.session import SessionLocal
from app.services.rss_ingestion import ingest_configured_rss_feeds


def main() -> None:
    with SessionLocal() as session:
        results = ingest_configured_rss_feeds(session)

    print(json.dumps([asdict(result) for result in results], indent=2))


if __name__ == "__main__":
    main()
