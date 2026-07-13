"""Policy-gated literal UTF-8 text search constrained to one workspace."""

import heapq
import json
from pathlib import Path
from typing import Any

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult
from netstudio.tools.workspace_paths import is_internal_path

DEFAULT_MAX_FILES = 1000
DEFAULT_MAX_RESULTS = 200
DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES = 1024 * 1024


class SearchTextTool(Tool):
    """Search bounded regular UTF-8 files without following symlinks."""

    def __init__(self, workspace_root: Path, max_files: int = DEFAULT_MAX_FILES, max_results: int = DEFAULT_MAX_RESULTS, max_file_size_bytes: int = DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES) -> None:
        if max_files <= 0 or max_results <= 0 or max_file_size_bytes <= 0:
            raise ValueError("search limits must be greater than zero")
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._max_files = max_files
        self._max_results = max_results
        self._max_file_size_bytes = max_file_size_bytes

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(name="search_text", description="Search literal text in bounded UTF-8 regular files inside the authorized workspace; line and column are 1-based and symlinks are not followed", capabilities=frozenset({ToolCapability.READ}), argument_schema={"type": "object", "properties": {"query": {"type": "string", "minLength": 1}, "path": {"type": "string", "minLength": 1, "default": "."}, "case_sensitive": {"type": "boolean", "default": False}}, "required": ["query"], "additionalProperties": False})

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        validation_error = self._validate_arguments(arguments)
        if validation_error is not None:
            return self._failure("invalid_arguments", validation_error)
        query = arguments["query"]
        requested = arguments.get("path", ".")
        case_sensitive = arguments.get("case_sensitive", False)
        raw_root = self._workspace_root / Path(requested)
        try:
            root = raw_root.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            return self._failure("search_failed", f"Path resolution failed: {exc}")
        if not root.is_relative_to(self._workspace_root):
            return self._failure("path_outside_workspace", "Path resolves outside the authorized workspace")
        if is_internal_path(self._workspace_root, root):
            return self._failure("reserved_internal_path", "Reserved NetStudio area is inaccessible")
        if not root.exists():
            return self._failure("path_not_found", "Path does not exist")
        if raw_root.is_symlink():
            return self._failure("search_failed", "Symlink roots are not searched")
        try:
            files, files_truncated = self._files_to_search(root)
        except OSError as exc:
            return self._failure("search_failed", f"Unable to enumerate search root: {exc}")
        matches: list[dict[str, str | int]] = []
        files_examined = 0
        skipped_invalid_utf8 = 0
        skipped_too_large = 0
        results_truncated = False
        for file_path in files:
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            if size > self._max_file_size_bytes:
                skipped_too_large += 1
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped_invalid_utf8 += 1
                continue
            except OSError:
                continue
            files_examined += 1
            relative = file_path.relative_to(self._workspace_root).as_posix()
            for line_number, line in enumerate(content.splitlines(), start=1):
                for column in self._columns(line, query, case_sensitive):
                    if len(matches) >= self._max_results:
                        results_truncated = True
                        break
                    matches.append({"path": relative, "line": line_number, "column": column, "text": line})
                if results_truncated:
                    break
            if results_truncated:
                break
        root_relative = root.relative_to(self._workspace_root).as_posix() or "."
        return ToolResult(success=True, output=json.dumps({"matches": matches}, ensure_ascii=False, sort_keys=True), metadata={"query": query, "root": root_relative, "case_sensitive": case_sensitive, "files_examined": files_examined, "matches_count": len(matches), "truncated": files_truncated or results_truncated, "skipped_invalid_utf8": skipped_invalid_utf8, "skipped_too_large": skipped_too_large})

    def _files_to_search(self, root: Path) -> tuple[list[Path], bool]:
        if root.is_file():
            return [root], False
        if not root.is_dir():
            raise OSError("Search root is not a regular file or directory")
        frontier: list[tuple[str, Path]] = []
        for child in root.iterdir():
            if not is_internal_path(self._workspace_root, child):
                heapq.heappush(frontier, (self._relative(child), child))
        files: list[Path] = []
        while frontier:
            _, current = heapq.heappop(frontier)
            if current.is_symlink() or is_internal_path(self._workspace_root, current):
                continue
            if current.is_dir():
                for child in current.iterdir():
                    if not is_internal_path(self._workspace_root, child):
                        heapq.heappush(frontier, (self._relative(child), child))
                continue
            if current.is_file():
                files.append(current)
                if len(files) > self._max_files:
                    return files[: self._max_files], True
        return files, False

    def _columns(self, line: str, query: str, case_sensitive: bool) -> list[int]:
        if case_sensitive:
            return self._literal_columns(line, query)
        folded_line, offsets = self._casefold_with_offsets(line)
        folded_query = query.casefold()
        columns: list[int] = []
        start = 0
        while True:
            index = folded_line.find(folded_query, start)
            if index < 0:
                return columns
            columns.append(offsets[index] + 1)
            start = index + max(len(folded_query), 1)

    def _literal_columns(self, line: str, query: str) -> list[int]:
        columns: list[int] = []
        start = 0
        while True:
            index = line.find(query, start)
            if index < 0:
                return columns
            columns.append(index + 1)
            start = index + len(query)

    def _casefold_with_offsets(self, value: str) -> tuple[str, list[int]]:
        folded_parts: list[str] = []
        offsets: list[int] = []
        for index, character in enumerate(value):
            folded = character.casefold()
            folded_parts.append(folded)
            offsets.extend([index] * len(folded))
        return "".join(folded_parts), offsets

    def _relative(self, path: Path) -> str:
        return path.relative_to(self._workspace_root).as_posix()

    def _validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        unexpected = set(arguments) - {"query", "path", "case_sensitive"}
        if unexpected:
            return f"Unsupported arguments: {', '.join(sorted(unexpected))}"
        if "query" not in arguments:
            return "query is required"
        query = arguments["query"]
        if not isinstance(query, str):
            return "query must be a string"
        if not query:
            return "query must not be empty"
        path = arguments.get("path", ".")
        if not isinstance(path, str):
            return "path must be a string"
        if not path.strip():
            return "path must not be empty"
        case_sensitive = arguments.get("case_sensitive", False)
        if not isinstance(case_sensitive, bool):
            return "case_sensitive must be a boolean"
        return None

    def _failure(self, code: str, message: str) -> ToolResult:
        return ToolResult(success=False, error=message, metadata={"code": code})
