from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse, AgentRunHistoryResponse
from app.schemas.live_web import LiveWebSearchRequest, LiveWebSearchResponse
from app.services.agents import list_agent_runs, run_agent_query
from app.services.live_web_research import run_live_web_search


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agents(request: AgentQueryRequest, db: Session = Depends(get_db)) -> AgentQueryResponse:
    return run_agent_query(request, db)


@router.get("/runs", response_model=AgentRunHistoryResponse)
def read_agent_runs(
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AgentRunHistoryResponse:
    return list_agent_runs(db, limit=limit)


@router.post("/live-web/search", response_model=LiveWebSearchResponse)
def search_live_web(request: LiveWebSearchRequest) -> LiveWebSearchResponse:
    return run_live_web_search(request)
