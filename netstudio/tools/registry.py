"""Policy-filtered tool registry."""

from netstudio.runtime.context import ExecutionContext
from netstudio.tools.base import Tool


class DuplicateToolError(ValueError):
    """Raised when a tool name is registered more than once."""


class ToolNotFoundError(LookupError):
    """Raised when a tool name is not registered."""


class ToolRegistry:
    """Owns tools and exposes only policy-permitted views."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register one tool under its unique metadata name."""
        name = tool.metadata.name
        if name in self._tools:
            raise DuplicateToolError(f"Tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool:
        """Locate a registered tool by name."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool not found: {name}") from exc

    def view(self, context: ExecutionContext) -> "ToolRegistryView":
        """Build a filtered registry view for one execution context."""
        permitted = {
            name: tool
            for name, tool in self._tools.items()
            if context.policy.permits(tool.metadata.capabilities)
        }
        return ToolRegistryView(permitted)


class ToolRegistryView:
    """Read-only policy-filtered tool view used by the runtime."""

    def __init__(self, tools: dict[str, Tool]) -> None:
        self._tools = dict(tools)

    def get(self, name: str) -> Tool:
        """Locate a permitted tool by name."""
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolNotFoundError(f"Tool unavailable in execution policy: {name}") from exc

    def names(self) -> tuple[str, ...]:
        """Return permitted tool names."""
        return tuple(self._tools)
