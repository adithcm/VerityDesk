from fastapi import APIRouter

from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.services.agents import run_agent_query


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agents(request: AgentQueryRequest) -> AgentQueryResponse:
    return run_agent_query(request)
