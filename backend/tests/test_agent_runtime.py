import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import AgentRun
from app.schemas.agent import AgentContext, AgentQueryRequest, AgentResult
from app.services.agent_runtime import AgentRegistry, AgentRunLogger, AgentRuntime, build_agent_context


class FakeAgent:
    name = "FakeAgent"

    def run(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            summary=f"Handled {context.user_query}",
            confidence="medium",
            risks=["Test risk"],
            follow_up_questions=["Test follow-up?"],
        )


class FailingAgent:
    name = "FailingAgent"

    def run(self, context: AgentContext) -> AgentResult:
        raise RuntimeError("agent failed")


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return TestingSessionLocal()


def test_build_agent_context_carries_request_fields() -> None:
    request = AgentQueryRequest(
        user_query="What matters for SPY today?",
        intent="market_research",
        domains=["Markets and Rates"],
        tickers=["SPY"],
        regions=["US"],
        time_window="today",
    )

    context = build_agent_context("request-1", request)

    assert context.request_id == "request-1"
    assert context.user_query == request.user_query
    assert context.intent == "market_research"
    assert context.domains == ["Markets and Rates"]
    assert context.tickers == ["SPY"]
    assert context.regions == ["US"]
    assert context.time_window == "today"
    assert context.safety_level == "investment_research"


def test_agent_registry_registers_and_retrieves_agents() -> None:
    registry = AgentRegistry()
    agent = FakeAgent()

    registry.register(agent)

    assert registry.get("FakeAgent") is agent
    assert registry.names() == ["FakeAgent"]


def test_agent_registry_rejects_duplicate_agent_names() -> None:
    registry = AgentRegistry()
    registry.register(FakeAgent())

    with pytest.raises(ValueError, match="Agent already registered"):
        registry.register(FakeAgent())


def test_agent_runtime_runs_agent_and_logs_success() -> None:
    request = AgentQueryRequest(user_query="Give me a market update")
    context = build_agent_context("request-2", request)
    registry = AgentRegistry()
    registry.register(FakeAgent())

    with build_session() as session:
        runtime = AgentRuntime(registry, AgentRunLogger(session))
        result = runtime.run("FakeAgent", context)
        session.commit()

        run = session.scalars(select(AgentRun)).one()

    assert result.agent_name == "FakeAgent"
    assert result.summary == "Handled Give me a market update"
    assert run.request_id == "request-2"
    assert run.agent_name == "FakeAgent"
    assert run.status == "success"
    assert run.input["user_query"] == "Give me a market update"
    assert run.output["summary"] == "Handled Give me a market update"
    assert run.started_at is not None
    assert run.completed_at is not None


def test_agent_runtime_logs_failures() -> None:
    request = AgentQueryRequest(user_query="Break")
    context = build_agent_context("request-3", request)
    registry = AgentRegistry()
    registry.register(FailingAgent())

    with build_session() as session:
        runtime = AgentRuntime(registry, AgentRunLogger(session))

        with pytest.raises(RuntimeError, match="agent failed"):
            runtime.run("FailingAgent", context)

        session.commit()
        run = session.scalars(select(AgentRun)).one()

    assert run.status == "failed"
    assert run.error == "agent failed"
    assert run.completed_at is not None
