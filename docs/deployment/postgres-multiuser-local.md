# Postgres Multi-User Local Setup

This branch adds the first multi-user foundation:

- `users` stores local VerityDesk accounts.
- `user_sessions` stores server-side login sessions.
- `user_settings.user_id` links each account to its own settings/profile row.
- `user_settings.profile_metadata` stores the account personalization profile used by the UI and prompts.

## Start Postgres

```bash
make postgres-up
```

The local Docker database uses:

- database: `veritydesk`
- user: `veritydesk`
- password: `veritydesk`
- port: `5433` from your Mac, `5432` inside Docker

To point the local backend at Postgres instead of SQLite, set this in `.env` before running `make app-dev`:

```bash
DATABASE_URL=postgresql+psycopg://veritydesk:veritydesk@localhost:5433/veritydesk
OWNER_EMAIL=your-email@example.com
```

Then run:

```bash
make db-upgrade
make app-dev
```

## View Postgres

Open a `psql` shell:

```bash
make postgres-shell
```

Useful commands inside `psql`:

```sql
\l
\c veritydesk
\dt
\d users
\d user_settings
select id, email, display_name, setup_complete, created_at from users;
select id, user_id, watchlist_tickers, preferred_regions, profile_metadata from user_settings;
select id, user_id, expires_at, revoked_at, last_seen_at from user_sessions;
\q
```

DBeaver connection settings:

- Host: `localhost`
- Port: `5433`
- Database: `veritydesk`
- Username: `veritydesk`
- Password: `veritydesk`

Quick table list without opening an interactive shell:

```bash
make postgres-tables
```

## UI Flow

The app now requires login before the dashboard can be opened.

If the account email matches `OWNER_EMAIL`, VerityDesk preloads the owner profile with:

- Phoenix, AZ as the starting location.
- Arizona housing markets.
- S&P 500 plus major tech tickers.
- World news, geopolitics, U.S. news, AI/major tech, and markets/watchlist as daily briefing priorities.

Other new accounts start with a generic profile and `setup_complete=false`, so the setup screen opens and asks the user for their own location, watchlist, interests, and briefing preferences. Saving Settings writes that user's profile back to the backend database.
