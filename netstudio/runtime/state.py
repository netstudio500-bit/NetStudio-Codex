"""Explicit runtime states and validated transitions."""

from enum import Enum


class RuntimeState(str, Enum):
    """Lifecycle states for one agent runtime execution."""

    IDLE = "IDLE"
    PLANNING = "PLANNING"
    WAITING_PERMISSION = "WAITING_PERMISSION"
    RUNNING_TOOL = "RUNNING_TOOL"
    VALIDATING = "VALIDATING"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = frozenset(
    {RuntimeState.COMPLETED, RuntimeState.FAILED, RuntimeState.CANCELLED}
)

_ALLOWED_TRANSITIONS: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.IDLE: frozenset({RuntimeState.PLANNING, RuntimeState.CANCELLED}),
    RuntimeState.PLANNING: frozenset(
        {
            RuntimeState.WAITING_PERMISSION,
            RuntimeState.COMPLETED,
            RuntimeState.FAILED,
            RuntimeState.CANCELLED,
        }
    ),
    RuntimeState.WAITING_PERMISSION: frozenset(
        {RuntimeState.RUNNING_TOOL, RuntimeState.FAILED, RuntimeState.CANCELLED}
    ),
    RuntimeState.RUNNING_TOOL: frozenset(
        {RuntimeState.VALIDATING, RuntimeState.FAILED, RuntimeState.CANCELLED}
    ),
    RuntimeState.VALIDATING: frozenset(
        {RuntimeState.REPLANNING, RuntimeState.FAILED, RuntimeState.CANCELLED}
    ),
    RuntimeState.REPLANNING: frozenset(
        {
            RuntimeState.WAITING_PERMISSION,
            RuntimeState.COMPLETED,
            RuntimeState.FAILED,
            RuntimeState.CANCELLED,
        }
    ),
    RuntimeState.COMPLETED: frozenset(),
    RuntimeState.FAILED: frozenset(),
    RuntimeState.CANCELLED: frozenset(),
}


class InvalidStateTransition(ValueError):
    """Raised when the runtime lifecycle attempts an invalid transition."""


def validate_transition(current: RuntimeState, target: RuntimeState) -> None:
    """Validate one runtime state transition."""
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(
            f"Invalid runtime transition: {current.value} -> {target.value}"
        )
