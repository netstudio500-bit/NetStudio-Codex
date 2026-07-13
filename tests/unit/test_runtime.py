"""Behavior tests for the first executable AgentRuntime vertical slice."""

from typing import Any

import pytest

from netstudio.runtime import (
    AgentRuntime,
    DecisionKind,
    ExecutionContext,
    InvalidStateTransition,
    Observation,
    PolicySnapshot,
    RuntimeDecision,
    RuntimeState,
    ScopeRef,
)
from netstudio.tools import Tool, ToolCapability, ToolMetadata, ToolRegistry, ToolResult


class SequenceDecisionSource:
    """Deterministic real decision source that consumes a decision sequence."""

    def __init__(self, decisions: list[RuntimeDecision]) -> None:
        self.decisions = iter(decisions)
        self.observations_seen: list[tuple[Observation, ...]] = []

    async def decide(
        self, task: str, observations: tuple[Observation, ...], iteration: int
    ) -> RuntimeDecision:
        self.observations_seen.append(observations)
        return next(self.decisions)


class EchoTool(Tool):
    """Concrete test tool exercising the real Tool contract."""

    def __init__(
        self, capability: ToolCapability = ToolCapability.READ, success: bool = True
    ) -> None:
        self._capability = capability
        self._success = success
        self.executions: list[dict[str, Any]] = []

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="echo",
            description="Echo one value",
            capabilities=frozenset({self._capability}),
            argument_schema={
                "type": "object",
                "properties": {"value": {}},
                "required": ["value"],
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        self.executions.append(arguments)
        if not self._success:
            return ToolResult(success=False, error="echo failed")
        return ToolResult(success=True, output=str(arguments["value"]))


def context(*capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        scope=ScopeRef("test-scope"),
        policy=PolicySnapshot(frozenset(capabilities)),
    )


def runtime(
    decisions: list[RuntimeDecision],
    registry: ToolRegistry | None = None,
    execution_context: ExecutionContext | None = None,
    max_iterations: int = 8,
) -> AgentRuntime:
    return AgentRuntime(
        decision_source=SequenceDecisionSource(decisions),
        registry=registry or ToolRegistry(),
        context=execution_context or context(),
        max_iterations=max_iterations,
    )


def test_runtime_accepts_valid_state_transition() -> None:
    agent_runtime = runtime([])

    agent_runtime.transition_to(RuntimeState.PLANNING)

    assert agent_runtime.state is RuntimeState.PLANNING


def test_runtime_rejects_invalid_state_transition() -> None:
    agent_runtime = runtime([])

    with pytest.raises(InvalidStateTransition, match="IDLE -> COMPLETED"):
        agent_runtime.transition_to(RuntimeState.COMPLETED)


@pytest.mark.asyncio
async def test_runtime_stops_at_max_iterations() -> None:
    tool = EchoTool()
    registry = ToolRegistry()
    registry.register(tool)
    decisions = [RuntimeDecision(DecisionKind.TOOL, "echo", {"value": index}) for index in range(2)]
    agent_runtime = runtime(decisions, registry, context(ToolCapability.READ), max_iterations=2)

    result = await agent_runtime.run("repeat")

    assert result.state is RuntimeState.FAILED
    assert result.failure is not None
    assert result.failure.code == "max_iterations_exceeded"
    assert len(tool.executions) == 2


@pytest.mark.asyncio
async def test_runtime_completes_explicitly() -> None:
    agent_runtime = runtime([RuntimeDecision(DecisionKind.COMPLETE, output="done")])

    result = await agent_runtime.run("finish")

    assert result.state is RuntimeState.COMPLETED
    assert result.output == "done"
    assert result.failure is None


@pytest.mark.asyncio
async def test_runtime_fails_on_invalid_decision() -> None:
    agent_runtime = runtime([RuntimeDecision(DecisionKind.TOOL)])

    result = await agent_runtime.run("invalid")

    assert result.state is RuntimeState.FAILED
    assert result.failure is not None
    assert result.failure.code == "invalid_decision"


@pytest.mark.asyncio
async def test_runtime_can_be_cancelled() -> None:
    agent_runtime = runtime([RuntimeDecision(DecisionKind.CANCEL, output="cancelled")])

    result = await agent_runtime.run("cancel")

    assert result.state is RuntimeState.CANCELLED
    assert result.output == "cancelled"


@pytest.mark.asyncio
async def test_runtime_does_not_execute_policy_denied_tool() -> None:
    tool = EchoTool(ToolCapability.WRITE)
    registry = ToolRegistry()
    registry.register(tool)
    agent_runtime = runtime(
        [RuntimeDecision(DecisionKind.TOOL, "echo", {"value": "blocked"})],
        registry,
        context(ToolCapability.READ),
    )

    result = await agent_runtime.run("blocked")

    assert result.state is RuntimeState.FAILED
    assert result.failure is not None
    assert result.failure.code == "tool_denied_or_missing"
    assert tool.executions == []


@pytest.mark.asyncio
async def test_runtime_does_not_execute_tool_with_invalid_arguments() -> None:
    tool = EchoTool()
    registry = ToolRegistry()
    registry.register(tool)
    agent_runtime = runtime(
        [RuntimeDecision(DecisionKind.TOOL, "echo", {"unexpected": "value"})],
        registry,
        context(ToolCapability.READ),
    )

    result = await agent_runtime.run("invalid arguments")

    assert result.state is RuntimeState.FAILED
    assert result.failure is not None
    assert result.failure.code == "invalid_tool_arguments"
    assert tool.executions == []


@pytest.mark.asyncio
async def test_tool_result_becomes_observation_for_next_decision() -> None:
    tool = EchoTool()
    registry = ToolRegistry()
    registry.register(tool)
    source = SequenceDecisionSource(
        [
            RuntimeDecision(DecisionKind.TOOL, "echo", {"value": "observed"}),
            RuntimeDecision(DecisionKind.COMPLETE, output="finished"),
        ]
    )
    agent_runtime = AgentRuntime(source, registry, context(ToolCapability.READ))

    result = await agent_runtime.run("use tool")

    assert result.state is RuntimeState.COMPLETED
    assert result.observations[0].result.output == "observed"
    assert source.observations_seen[0] == ()
    second_observations = source.observations_seen[1]
    assert len(second_observations) == 1
    assert result.observations[0] is second_observations[0]


@pytest.mark.asyncio
async def test_failed_tool_produces_structured_runtime_failure() -> None:
    tool = EchoTool(success=False)
    registry = ToolRegistry()
    registry.register(tool)
    agent_runtime = runtime(
        [RuntimeDecision(DecisionKind.TOOL, "echo", {"value": "fail"})],
        registry,
        context(ToolCapability.READ),
    )

    result = await agent_runtime.run("fail")

    assert result.state is RuntimeState.FAILED
    assert result.failure is not None
    assert result.failure.code == "tool_execution_failed"
    assert result.failure.message == "echo failed"
