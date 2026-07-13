"""Executable tool contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from netstudio.runtime.capabilities import ToolCapability


@dataclass(frozen=True)
class ToolMetadata:
    """Static identity and capability declaration for a tool."""

    name: str
    description: str
    capabilities: frozenset[ToolCapability]


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by every tool execution."""

    success: bool
    output: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Executable tool interface."""

    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return the tool's explicit metadata."""

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated runtime arguments."""
