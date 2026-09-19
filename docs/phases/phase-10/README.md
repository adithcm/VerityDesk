# Phase 10: Desktop Deployment

Status: In progress

Purpose: turn VerityDesk from a local developer workflow into a clickable macOS desktop app that starts its own services, stores user data locally, and can be updated later without wiping saved profiles, chats, reports, or briefings.

## Product Decision

The first deployment target is a local macOS desktop app named VerityDesk.

Development will continue to support Docker/Postgres because it is useful for database inspection and closer to hosted production. The packaged desktop app should not require Docker Desktop, Postgres.app, or terminal commands. It will use an app-managed local database path and run backend migrations on startup.

## Milestones

1. [10.1 Deployment architecture](milestones/10.1-deployment-architecture.md)
2. [10.2 Desktop runtime shell](milestones/10.2-desktop-runtime-shell.md)
3. [10.3 Packaged database mode](milestones/10.3-packaged-database-mode.md)
4. [10.4 API key and local config handling](milestones/10.4-api-key-and-local-config.md)
5. [10.5 Production builds](milestones/10.5-production-builds.md)
6. [10.6 macOS app packaging](milestones/10.6-macos-app-packaging.md)
7. [10.7 Deployment validation](milestones/10.7-deployment-validation.md)
8. [10.8 Clean simple documentation](milestones/10.8-clean-simple-documentation.md)

## Final User Experience Target

- User opens `VerityDesk.app` from Finder or the Dock.
- The app starts the backend and web UI automatically.
- The user sees a login/setup screen, then their own saved workspace.
- The app can run daily refreshes while it is open.
- User data persists across close/reopen and app updates.
- Docker is not required for the packaged desktop app.
