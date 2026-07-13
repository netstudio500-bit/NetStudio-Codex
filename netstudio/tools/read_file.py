"""Policy-gated UTF-8 text file reading constrained to one workspace."""

from pathlib import Path
from typing import Any

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult

DEFAULT_MAX_FILE_SIZE_BYTES = 1024 * 1024


class ReadFileTool(Tool):
    """Read one bounded UTF-8 text file inside the authorized workspace."""

    def __init__(
        self,
        workspace_root: Path,
        max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    ) -> None:
        if max_file_size_bytes <= 0:
            raise ValueError("max_file_size_bytes must be greater than zero")
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._max_file_size_bytes = max_file_size_bytes

    @property
    def metadata(self) -> ToolMetadata:
        """Declare the read_file contract and READ capability."""
        return ToolMetadata(
            name="read_file",
            description="Read one UTF-8 text file inside the authorized workspace",
            capabilities=frozenset({ToolCapability.READ}),
            argument_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "minLength": 1}},
                "required": ["path"],
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate, resolve and read one bounded UTF-8 file."""
        validation_error = self._validate_arguments(arguments)
        if validation_error is not None:
            return self._failure("invalid_arguments", validation_error)

        requested_path = Path(arguments["path"])
        try:
            resolved_path = (self._workspace_root / requested_path).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            return self._failure("read_failed", f"Path resolution failed: {exc}")

        if not resolved_path.is_relative_to(self._workspace_root):
            return self._failure(
                "path_outside_workspace", "Path resolves outside the authorized workspace"
            )
        if not resolved_path.exists():
            return self._failure("file_not_found", "File does not exist")
        if not resolved_path.is_file():
            return self._failure("not_a_file", "Path is not a regular file")

        try:
            size = resolved_path.stat().st_size
        except OSError as exc:
            return self._failure("read_failed", f"Unable to inspect file: {exc}")
        if size > self._max_file_size_bytes:
            return self._failure(
                "file_too_large",
                f"File exceeds maximum size of {self._max_file_size_bytes} bytes",
            )

        try:
            content = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return self._failure("invalid_utf8", "File is not valid UTF-8 text")
        except OSError as exc:
            return self._failure("read_failed", f"Unable to read file: {exc}")

        relative_path = resolved_path.relative_to(self._workspace_root)
        return ToolResult(
            success=True,
            output=content,
            metadata={
                "path": relative_path.as_posix(),
                "size": size,
                "encoding": "utf-8",
            },
        )

    def _validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        unexpected = set(arguments) - {"path"}
        if unexpected:
            return f"Unsupported arguments: {', '.join(sorted(unexpected))}"
        if "path" not in arguments:
            return "path is required"
        path = arguments["path"]
        if not isinstance(path, str):
            return "path must be a string"
        if not path.strip():
            return "path must not be empty"
        return None

    def _failure(self, code: str, message: str) -> ToolResult:
        return ToolResult(success=False, error=message, metadata={"code": code})
