# Database And Persistence

VerityDesk stores users, settings, chats, reports, source health, ingested articles, economic observations, agent runs, and watch items in a relational database.

The app supports two database modes:

- SQLite for the packaged desktop app
- Postgres for local development and future hosted/multiuser deployment paths

## Database Modes

| Mode | Used By | Default Location |
| --- | --- | --- |
| SQLite | Packaged macOS desktop app | `~/Library/Application Support/VerityDesk/veritydesk.db` |
| Postgres | Local development and multiuser validation | `postgresql://veritydesk:veritydesk@localhost:5432/veritydesk` |

The desktop app is designed to work without Docker or Postgres. It starts the backend with a SQLite `DATABASE_URL`, runs migrations, and keeps data in the macOS Application Support folder.

Development can use Postgres through Docker Compose so tables, relationships, and multiuser behavior can be inspected more easily.

## Entity Map

```mermaid
erDiagram
    users ||--o| user_settings : has
    users ||--o{ user_sessions : creates
    users ||--o{ reports : owns

    sources ||--o{ articles : publishes
    sources ||--o{ economic_observations : provides
    sources ||--o{ ingestion_runs : tracks
    sources ||--o| source_health : reports
    sources ||--o{ retrieved_snapshots : retrieves
    sources ||--o{ citations : supports

    articles ||--o{ citations : cited_by
    articles ||--o{ retrieved_snapshots : snapshots
    articles ||--o{ external_ids : has
    economic_observations ||--o{ external_ids : has

    reports ||--o{ citations : includes
    watch_items ||--o{ watch_alerts : triggers
    reports ||--o{ watch_alerts : may_support
```

## Main Tables

| Table | Purpose |
| --- | --- |
| `users` | Login accounts, display names, password hashes, setup status, active flag. |
| `user_sessions` | Session tokens, expirations, revocation, and last-seen tracking. |
| `user_settings` | Per-user watchlist, preferred regions, enabled sources, profile metadata, daily schedule settings, API-key status, and disclaimer acknowledgement. |
| `sources` | Source catalog records, domains, access methods, reliability tier, storage rules, and source policy metadata. |
| `articles` | Ingested article/feed metadata, summaries, excerpts, domains, tickers, companies, regions, and storage policy. |
| `economic_observations` | Structured time-series observations such as rates, labor data, housing indexes, quotes, and Census values. |
| `ingestion_runs` | Manual or scheduled ingestion attempts, status, item counts, timestamps, and errors. |
| `source_health` | Latest source status, last success, failures, newest item, freshness window, and troubleshooting message. |
| `retrieved_snapshots` | Retrieval metadata and hashes for fetched URLs. |
| `external_ids` | Mapping between local records and provider/source identifiers. |
| `reports` | Saved daily briefings, generated reports, summaries, markdown body, confidence, domains, tickers, companies, and guardrail status. |
| `citations` | Report citations linked to sources and articles. |
| `agent_runs` | Agent execution logs with request id, agent name, input context, output payload, status, and errors. |
| `watch_items` | User-defined or app-defined watch queries for proactive monitoring. |
| `watch_alerts` | Alerts triggered from watch items, with status and optional report link. |

## User Isolation

User-facing state is scoped by account wherever personalization matters:

- `users`
- `user_sessions`
- `user_settings`
- `reports`

Shared source data, such as articles and economic observations, is stored once and reused as evidence. This prevents every user from duplicating the same source records. Personalization happens when agents combine shared evidence with each user's settings, watchlist, regions, and briefing preferences.

## Shared Evidence Versus Personal Data

```mermaid
flowchart LR
    Shared["Shared source evidence"] --> Agents["Agent workflow"]
    Personal["User settings and chat context"] --> Agents
    Agents --> Reports["User-owned reports"]
    Agents --> Chat["User chat response"]

    Shared --> Articles["articles"]
    Shared --> Observations["economic_observations"]
    Shared --> Health["source_health"]

    Personal --> Settings["user_settings"]
    Personal --> Sessions["user_sessions"]
    Reports --> UserReports["reports.user_id"]
```

Shared:

- source catalog
- ingested article metadata
- structured observations
- source health
- ingestion runs

Personal:

- account profile
- login sessions
- setup answers
- regions and watchlist
- daily briefing preferences
- saved reports

## Migrations

Alembic owns schema changes.

Run migrations in development:

```bash
make db-upgrade
```

The desktop app runs migrations on startup against its app-managed SQLite database.

## Inspecting Postgres

Start Postgres:

```bash
make postgres-up
```

Run migrations:

```bash
make db-upgrade
```

Open an interactive shell:

```bash
make postgres-shell
```

DBeaver connection values:

```text
Host: localhost
Port: 5432
Database: veritydesk
Username: veritydesk
Password: veritydesk
```

If your local Postgres was configured with a different port, use the port from the running container or local server.

## Inspecting Desktop SQLite

The packaged app database lives at:

```text
~/Library/Application Support/VerityDesk/veritydesk.db
```

Use DBeaver or DB Browser for SQLite:

```text
Database type: SQLite
Database file: /Users/<you>/Library/Application Support/VerityDesk/veritydesk.db
```

Close the app before doing manual database edits. Reading while the app is open is usually fine, but writes can conflict with the running backend.

## Data Safety

- Real API keys are not stored in the repo.
- Desktop keys live in `config.env` under macOS Application Support.
- Passwords are stored as hashes, not plaintext.
- The app stores article metadata, excerpts, and summaries based on source policy rather than copying full articles by default.
- Desktop data persists across app close/reopen and should survive app updates as long as the Application Support folder is kept.

## Future Database Work

- Hosted Postgres deployment for multi-device sync.
- Stronger account-management flows, password reset, and email verification.
- Keychain-backed secrets instead of file-based desktop config.
- Per-user chat persistence across devices.
- Data retention controls and export/delete tools.
