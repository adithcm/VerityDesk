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

## Desktop Database Mode

When the Electron desktop shell starts, it sets `DATABASE_URL` for the backend and migration process. The default value points at the app-managed SQLite database:

```text
sqlite:////Users/<you>/Library/Application Support/VerityDesk/veritydesk.db
```

You can override the desktop data path during development:

```bash
VERITYDESK_DESKTOP_DATA_DIR=/tmp/veritydesk-data make desktop-dev
```

This does not affect the normal developer Postgres flow used by `make app-dev`.

## Remaining Phase 10 Work

- Add Electron runtime shell.
- Add packaged database startup mode.
- Add packaged API key/config handling.
- Add production build and packaging scripts.
- Generate a macOS `.app`.
- Write clean user-facing install/run docs.
