"""Controlled AgentRuntime loop for decisions, policy and tool observations."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from netstudio.runtime.context import ExecutionContext
from netstudio.runtime.state import TERMINAL_STATES, RuntimeState, validate_transition
from netstudio.tools.base import ToolResult
from netstudio.tools.registry import ToolNotFoundError, ToolRegistry


class DecisionKind(str, Enum):
    """Minimal linear decisions supported by the first runtime slice."""

    TOOL = "tool"
    COMPLETE = "complete"
    CANCEL = "cancel"


@dataclass(frozen=True)
class RuntimeDecision:
    """One decision consumed by the runtime."""

    kind: DecisionKind
    tool_name: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    output: str = ""


@dataclass(frozen=True)
class Observation:
    """A tool result fed back into the next decision."""

    tool_name: str
    result: ToolResult


@dataclass(frozen=True)
class RuntimeFailure:
    """Structured runtime failure preserved for callers and tests."""

    code: str
    message: str
    iteration: int


@dataclass(frozen=True)
class RuntimeResult:
    """Terminal result of one runtime execution."""

    state: RuntimeState
    output: str = ""
    observations: tuple[Observation, ...] = ()
    failure: RuntimeFailure | None = None


class DecisionSource(Protocol):
    """Future-compatible source of linear runtime decisions."""

    async def decide(
        self, task: str, observations: tuple[Observation, ...], iteration: int
    ) -> RuntimeDecision:
        """Return the next runtime decision."""


class AgentRuntime:
    """Execute a bounded decision/tool/observation lifecycle."""

    def __init__(
        self,
        decision_source: DecisionSource,
        registry: ToolRegistry,
        context: ExecutionContext,
        max_iterations: int = 8,
    ) -> None:
        if max_iterations <= 0:
            raise ValueError("max_iterations must be greater than zero")
        self._decision_source = decision_source
        self._registry = registry
        self._context = context
        self.max_iterations = max_iterations
        self.state = RuntimeState.IDLE
        self._observations: list[Observation] = []

    def transition_to(self, target: RuntimeState) -> None:
        """Apply one validated lifecycle transition."""
        validate_transition(self.state, target)
        self.state = target

    async def run(self, task: str) -> RuntimeResult:
        """Run decisions until explicit completion, failure or cancellation."""
        self.transition_to(RuntimeState.PLANNING)
        for iteration in range(1, self.max_iterations + 1):
            try:
                decision = await self._decision_source.decide(
                    task, tuple(self._observations), iteration
                )
                terminal = await self._apply_decision(decision, iteration)
            except Exception as exc:
                return self._fail("runtime_error", str(exc), iteration)
            if terminal is not None:
                return terminal

        return self._fail(
            "max_iterations_exceeded",
            f"Runtime exceeded max_iterations={self.max_iterations}",
            self.max_iterations,
        )

    async def _apply_decision(
        self, decision: RuntimeDecision, iteration: int
    ) -> RuntimeResult | None:
        if decision.kind is DecisionKind.COMPLETE:
            self.transition_to(RuntimeState.COMPLETED)
            return self._result(output=decision.output)
        if decision.kind is DecisionKind.CANCEL:
            self.transition_to(RuntimeState.CANCELLED)
            return self._result(output=decision.output)
        if decision.kind is not DecisionKind.TOOL or not decision.tool_name:
            return self._fail("invalid_decision", "Tool decision requires tool_name", iteration)

        self.transition_to(RuntimeState.WAITING_PERMISSION)
        permitted_registry = self._registry.view(self._context)
        try:
            tool = permitted_registry.get(decision.tool_name)
        except ToolNotFoundError as exc:
            return self._fail("tool_denied_or_missing", str(exc), iteration)

        self.transition_to(RuntimeState.RUNNING_TOOL)
        tool_result = await tool.execute(decision.arguments)
        self.transition_to(RuntimeState.VALIDATING)
        observation = Observation(tool_name=decision.tool_name, result=tool_result)
        self._observations.append(observation)
        if not tool_result.success:
            return self._fail(
                "tool_execution_failed",
                tool_result.error or f"Tool failed: {decision.tool_name}",
                iteration,
            )
        self.transition_to(RuntimeState.REPLANNING)
        return None

    def _fail(self, code: str, message: str, iteration: int) -> RuntimeResult:
        if self.state not in TERMINAL_STATES:
            self.transition_to(RuntimeState.FAILED)
        return self._result(failure=RuntimeFailure(code, message, iteration))

    def _result(
        self, output: str = "", failure: RuntimeFailure | None = None
    ) -> RuntimeResult:
        return RuntimeResult(
            state=self.state,
            output=output,
            observations=tuple(self._observations),
            failure=failure,
        )
