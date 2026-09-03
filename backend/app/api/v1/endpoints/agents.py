from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.agent import AgentQueryRequest, AgentQueryResponse
from app.services.agents import run_agent_query


router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/query", response_model=AgentQueryResponse)
def query_agents(request: AgentQueryRequest, db: Session = Depends(get_db)) -> AgentQueryResponse:
    return run_agent_query(request, db)
