from fastapi import APIRouter

from app.api.v1.endpoints import agents, ingestion, sources, system


api_router = APIRouter()
api_router.include_router(system.router, tags=["system"])
api_router.include_router(agents.router)
api_router.include_router(ingestion.router)
api_router.include_router(sources.router)
