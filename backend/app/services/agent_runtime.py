from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import AgentRun
from app.schemas.agent import AgentContext, AgentQueryRequest, AgentResult
from app.services.region_normalization import expand_regions, infer_regions_from_text


class BaseAgent(Protocol):
    name: str

    def run(self, context: AgentContext) -> AgentResult:
        """Run an agent against a shared request context."""


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        if agent.name in self._agents:
            raise ValueError(f"Agent already registered: {agent.name}")

        self._agents[agent.name] = agent

    def get(self, agent_name: str) -> BaseAgent:
        try:
            return self._agents[agent_name]
        except KeyError as error:
            raise KeyError(f"Unknown agent: {agent_name}") from error

    def names(self) -> list[str]:
        return list(self._agents)


class AgentRunLogger:
    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    def start(self, context: AgentContext, agent_name: str) -> AgentRun | None:
        if self.session is None:
            return None

        run = AgentRun(
            request_id=context.request_id,
            agent_name=agent_name,
            input=context.model_dump(),
            status="running",
            started_at=datetime.now(UTC),
        )
        self.session.add(run)
        self.session.flush()
        return run

    def complete(self, run: AgentRun | None, result: AgentResult) -> None:
        if self.session is None or run is None:
            return

        run.output = result.model_dump()
        run.status = "success"
        run.completed_at = datetime.now(UTC)
        self.session.flush()

    def fail(self, run: AgentRun | None, error: Exception) -> None:
        if self.session is None or run is None:
            return

        run.status = "failed"
        run.error = str(error)
        run.completed_at = datetime.now(UTC)
        self.session.flush()


class AgentRuntime:
    def __init__(self, registry: AgentRegistry, logger: AgentRunLogger | None = None) -> None:
        self.registry = registry
        self.logger = logger or AgentRunLogger()

    def run(self, agent_name: str, context: AgentContext) -> AgentResult:
        agent = self.registry.get(agent_name)
        run_record = self.logger.start(context, agent.name)

        try:
            result = agent.run(context)
        except Exception as error:
            self.logger.fail(run_record, error)
            raise

        self.logger.complete(run_record, result)
        return result


def build_agent_context(request_id: str, request: AgentQueryRequest) -> AgentContext:
    regions = expand_regions([*request.regions, *infer_regions_from_text(request.user_query)])
    return AgentContext(
        request_id=request_id,
        user_query=request.user_query,
        intent=request.intent,
        domains=request.domains,
        tickers=request.tickers,
        companies=request.companies,
        regions=regions,
        time_window=request.time_window,
        source_ids=request.source_ids,
        safety_level=request.safety_level,
    )
