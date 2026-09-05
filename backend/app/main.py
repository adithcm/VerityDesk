from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.services.scheduler import start_daily_scheduler, stop_daily_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = start_daily_scheduler()
    app.state.scheduler_task = scheduler_task
    try:
        yield
    finally:
        await stop_daily_scheduler(scheduler_task)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Local-first market intelligence backend.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["system"])
    def root_health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "investoragent-backend",
            "environment": settings.environment,
        }

    return app


app = create_app()
