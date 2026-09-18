# VerityDesk Desktop Deployment

Status: Draft for Phase 10

This document tracks the first installable macOS desktop version of VerityDesk.

## What The Desktop App Should Do

- Open as `VerityDesk.app`.
- Start the backend automatically.
- Show the VerityDesk UI without opening a terminal.
- Store user accounts, settings, chats, reports, briefings, and source data locally.
- Keep data after app updates.
- Avoid requiring Docker Desktop for normal use.

## Development Versus Packaged App

Development can still use Postgres:

```bash
make postgres-up
make db-upgrade
make app-dev
```

The packaged desktop app should use its own local database file:

```text
~/Library/Application Support/VerityDesk/veritydesk.db
```

That file can be inspected later with DBeaver or DB Browser for SQLite.

## Remaining Phase 10 Work

- Add Electron runtime shell.
- Add packaged database startup mode.
- Add packaged API key/config handling.
- Add production build and packaging scripts.
- Generate a macOS `.app`.
- Write clean user-facing install/run docs.

