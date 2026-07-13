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
from netstudio.tools.search_text import (
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES,
    SearchTextTool,
)
from netstudio.tools.shell import (
    DEFAULT_OUTPUT_LIMIT_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    ShellTool,
)
from netstudio.tools.write_file import (
    DEFAULT_MAX_DIFF_CHARS,
    DEFAULT_MAX_WRITE_SIZE_BYTES,
    WriteFileTool,
)

__all__ = [
    "DEFAULT_MAX_DIFF_CHARS",
    "DEFAULT_MAX_ENTRIES",
    "DEFAULT_MAX_FILES",
    "DEFAULT_MAX_FILE_SIZE_BYTES",
    "DEFAULT_MAX_RESULTS",
    "DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES",
    "DEFAULT_MAX_WRITE_SIZE_BYTES",
    "DEFAULT_OUTPUT_LIMIT_BYTES",
    "DEFAULT_TIMEOUT_SECONDS",
    "DuplicateToolError",
    "ListFilesTool",
    "MAX_TIMEOUT_SECONDS",
    "ReadFileTool",
    "SearchTextTool",
    "ShellTool",
    "Tool",
    "ToolCapability",
    "ToolMetadata",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolRegistryView",
    "ToolResult",
    "WriteFileTool",
]
