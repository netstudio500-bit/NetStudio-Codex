"""Policy-gated deterministic workspace discovery."""

import json
from pathlib import Path
from typing import Any

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult

DEFAULT_MAX_ENTRIES = 1000


class ListFilesTool(Tool):
    """List bounded workspace entries without following directory symlinks."""

    def __init__(self, workspace_root: Path, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be greater than zero")
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._max_entries = max_entries

    @property
    def metadata(self) -> ToolMetadata:
        """Declare the list_files contract and READ capability."""
        return ToolMetadata(
            name="list_files",
            description=(
                "List files, directories, and symlinks inside the authorized workspace; "
                "directory symlinks are never traversed"
            ),
            capabilities=frozenset({ToolCapability.READ}),
            argument_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1, "default": "."},
                    "recursive": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate, resolve, enumerate, and bound workspace entries."""
        validation_error = self._validate_arguments(arguments)
        if validation_error is not None:
            return self._failure("invalid_arguments", validation_error)

        requested = arguments.get("path", ".")
        recursive = arguments.get("recursive", False)
        try:
            root = (self._workspace_root / Path(requested)).resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            return self._failure("list_failed", f"Path resolution failed: {exc}")

        if not root.is_relative_to(self._workspace_root):
            return self._failure(
                "path_outside_workspace", "Path resolves outside the authorized workspace"
            )
        if not root.exists():
            return self._failure("path_not_found", "Path does not exist")
        if not root.is_dir():
            return self._failure("not_a_directory", "Path is not a directory")

        try:
            entries = self._enumerate(root, recursive)
        except OSError as exc:
            return self._failure("list_failed", f"Unable to enumerate directory: {exc}")

        truncated = len(entries) > self._max_entries
        selected = entries[: self._max_entries]
        root_relative = root.relative_to(self._workspace_root).as_posix() or "."
        return ToolResult(
            success=True,
            output=json.dumps({"entries": selected}, ensure_ascii=False, sort_keys=True),
            metadata={
                "root": root_relative,
                "recursive": recursive,
                "count": len(selected),
                "truncated": truncated,
            },
        )

    def _enumerate(self, root: Path, recursive: bool) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        self._visit(root, recursive, entries)
        return entries

    def _visit(self, directory: Path, recursive: bool, entries: list[dict[str, str]]) -> None:
        for child in sorted(directory.iterdir(), key=lambda path: path.name):
            entry = self._entry(child)
            if entry is not None:
                entries.append(entry)
                if len(entries) > self._max_entries:
                    return
            if recursive and child.is_dir() and not child.is_symlink():
                self._visit(child, recursive, entries)
                if len(entries) > self._max_entries:
                    return

    def _entry(self, path: Path) -> dict[str, str] | None:
        relative = path.relative_to(self._workspace_root).as_posix()
        if path.is_symlink():
            return {"path": relative, "type": "symlink"}
        if path.is_dir():
            return {"path": relative, "type": "directory"}
        if path.is_file():
            return {"path": relative, "type": "file"}
        return None

    def _validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        unexpected = set(arguments) - {"path", "recursive"}
        if unexpected:
            return f"Unsupported arguments: {', '.join(sorted(unexpected))}"
        path = arguments.get("path", ".")
        if not isinstance(path, str):
            return "path must be a string"
        if not path.strip():
            return "path must not be empty"
        recursive = arguments.get("recursive", False)
        if not isinstance(recursive, bool):
            return "recursive must be a boolean"
        return None

    def _failure(self, code: str, message: str) -> ToolResult:
        return ToolResult(success=False, error=message, metadata={"code": code})
