"""Runtime execution contracts."""

from netstudio.runtime.context import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.runtime.runtime import (
    AgentRuntime,
    DecisionKind,
    Observation,
    RuntimeDecision,
    RuntimeFailure,
    RuntimeResult,
)
from netstudio.runtime.state import InvalidStateTransition, RuntimeState

__all__ = [
    "AgentRuntime",
    "DecisionKind",
    "ExecutionContext",
    "InvalidStateTransition",
    "Observation",
    "PolicySnapshot",
    "RuntimeDecision",
    "RuntimeFailure",
    "RuntimeResult",
    "RuntimeState",
    "ScopeRef",
]
