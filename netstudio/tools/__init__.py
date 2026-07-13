"""Tool contracts and registry."""

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult
from netstudio.tools.list_files import DEFAULT_MAX_ENTRIES, ListFilesTool
from netstudio.tools.read_file import DEFAULT_MAX_FILE_SIZE_BYTES, ReadFileTool
from netstudio.tools.registry import (
    DuplicateToolError,
    ToolNotFoundError,
    ToolRegistry,
    ToolRegistryView,
)
from netstudio.tools.shell import (
    DEFAULT_OUTPUT_LIMIT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    ShellTool,
)

__all__ = [
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_OUTPUT_LIMIT_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "DuplicateToolError",
    "ListFilesTool",
    "MAX_TIMEOUT_SECONDS",
    "ReadFileTool",
    "ShellTool",
    "Tool",
    "ToolCapability",
    "ToolMetadata",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolRegistryView",
    "ToolResult",
]
