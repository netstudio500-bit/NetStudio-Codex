"""Execution scope and deny-by-default policy contracts."""

from dataclasses import dataclass, field
from pathlib import Path

from netstudio.runtime.capabilities import ToolCapability


@dataclass(frozen=True)
class ScopeRef:
    """Identifies the host-resolved scope and its authorized workspace root."""

    scope_id: str
    scope_type: str = "workspace"
    workspace_root: Path | None = None

    def resolved_workspace_root(self) -> Path:
        """Return the absolute workspace root resolved by the host."""
        return (self.workspace_root or Path.cwd()).resolve()


@dataclass(frozen=True)
class PolicySnapshot:
    """Immutable capability grant snapshot for one execution."""

    allowed_capabilities: frozenset[ToolCapability] = field(default_factory=frozenset)

    def permits(self, capabilities: frozenset[ToolCapability]) -> bool:
        """Return whether every declared capability is explicitly granted."""
        if not capabilities or ToolCapability.UNCLASSIFIED in capabilities:
            return False
        return capabilities.issubset(self.allowed_capabilities)


@dataclass(frozen=True)
class ExecutionContext:
    """Host-resolved execution scope and effective policy."""

    scope: ScopeRef
    policy: PolicySnapshot = field(default_factory=PolicySnapshot)
