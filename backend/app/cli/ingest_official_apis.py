import json
from dataclasses import asdict

from app.db.session import SessionLocal
from app.services.official_api_ingestion import ingest_configured_official_api_sources


def main() -> None:
    with SessionLocal() as session:
        results = ingest_configured_official_api_sources(session)

    print(json.dumps([asdict(result) for result in results], indent=2))


if __name__ == "__main__":
    main()
