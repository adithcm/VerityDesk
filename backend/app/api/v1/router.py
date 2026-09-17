from fastapi import APIRouter

from app.api.v1.endpoints import auth, agents, ingestion, preferences, reports, sources, suggestions, system, visuals, watchlist


api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(ingestion.router)
api_router.include_router(reports.router)
api_router.include_router(sources.router)
api_router.include_router(suggestions.router)
api_router.include_router(preferences.router)
api_router.include_router(watchlist.router)
api_router.include_router(visuals.router)
