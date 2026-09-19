# VerityDesk Desktop User Guide

This is the simple local guide for the first macOS desktop build.

## Open The App

The generated app is here:

```text
desktop/dist/mac-arm64/VerityDesk.app
```

Open it from Finder by double-clicking it.

If macOS blocks it because it is unsigned:

1. Right-click `VerityDesk.app`.
2. Choose `Open`.
3. Approve the warning.

The app can be dragged to the Dock after it opens.

## Build The App Again

From the project root:

```bash
make desktop-pack-mac
```

This rebuilds:

- The frontend production build.
- The app icon.
- The macOS `.app` bundle.

## API Keys

The desktop app reads keys from:

```text
~/Library/Application Support/VerityDesk/config.env
```

This file is local to your Mac account and is not committed to GitHub.

Main keys:

```bash
OPENAI_API_KEY=
TAVILY_API_KEY=
FRED_API_KEY=
CENSUS_API_KEY=
ALPHA_VANTAGE_API_KEY=
FINNHUB_API_KEY=
NEWSAPI_KEY=
```

## Local Database

The desktop app stores data here:

```text
~/Library/Application Support/VerityDesk/veritydesk.db
```

This stores local users, settings, chats, reports, briefings, and app data.

## View The Database In DBeaver

1. Open DBeaver.
2. Create a new SQLite connection.
3. Select this file:

```text
~/Library/Application Support/VerityDesk/veritydesk.db
```

4. Open the tables after the app has launched at least once.

## Development Database

Development can still use Postgres:

```bash
make postgres-up
make db-upgrade
make app-dev
```

The packaged desktop app does not require Docker or Postgres.

## What Is Not Final Yet

- The app is unsigned.
- There is no public installer/notarization yet.
- The app bundle is large because it includes Python, Node, backend, frontend, and dependencies.
- Keychain-based API key storage is planned later.

