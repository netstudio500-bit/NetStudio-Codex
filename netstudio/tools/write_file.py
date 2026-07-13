"""Policy-gated atomic UTF-8 writes constrained to one workspace."""

import difflib
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult
from netstudio.tools.workspace_paths import INTERNAL_DIRECTORY_NAME, is_internal_path

DEFAULT_MAX_WRITE_SIZE_BYTES = 1024 * 1024
DEFAULT_MAX_DIFF_CHARS = 64 * 1024


class WriteFileTool(Tool):
    """Create or overwrite one UTF-8 file with checkpoint and atomic replacement."""

    def __init__(
        self,
        workspace_root: Path,
        max_write_size_bytes: int = DEFAULT_MAX_WRITE_SIZE_BYTES,
        max_diff_chars: int = DEFAULT_MAX_DIFF_CHARS,
    ) -> None:
        if max_write_size_bytes <= 0 or max_diff_chars <= 0:
            raise ValueError("write and diff limits must be greater than zero")
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._max_write_size_bytes = max_write_size_bytes
        self._max_diff_chars = max_diff_chars

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description=(
                "Create or overwrite one UTF-8 file inside the authorized workspace using "
                "explicit intent, checkpointed overwrite, and atomic replacement"
            ),
            capabilities=frozenset({ToolCapability.WRITE}),
            argument_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "minLength": 1},
                    "content": {"type": "string"},
                    "create": {"type": "boolean", "default": False},
                    "overwrite": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        validation_error = self._validate_arguments(arguments)
        if validation_error is not None:
            return self._failure("invalid_arguments", validation_error)

        requested = Path(arguments["path"])
        content = arguments["content"]
        create = arguments.get("create", False)
        overwrite = arguments.get("overwrite", False)
        encoded = content.encode("utf-8")
        if len(encoded) > self._max_write_size_bytes:
            return self._failure("content_too_large", "UTF-8 content exceeds maximum write size")

        try:
            target = (self._workspace_root / requested).resolve(strict=False)
            parent = target.parent.resolve(strict=True)
        except FileNotFoundError:
            return self._failure("parent_not_found", "Parent directory does not exist")
        except (OSError, RuntimeError) as exc:
            return self._failure("write_failed", f"Path resolution failed: {exc}")

        if not target.is_relative_to(self._workspace_root) or not parent.is_relative_to(
            self._workspace_root
        ):
            return self._failure("path_outside_workspace", "Path resolves outside the workspace")
        if is_internal_path(self._workspace_root, target):
            return self._failure("reserved_internal_path", "Reserved NetStudio area is inaccessible")
        if target.exists() and target.is_dir():
            return self._failure("not_a_file", "Path is a directory")
        if target.is_symlink():
            return self._failure("write_failed", "Symlink targets are not writable")

        exists = target.exists()
        if not exists and not create:
            return self._failure("create_not_allowed", "File does not exist and create is false")
        if exists and not overwrite:
            return self._failure("overwrite_not_allowed", "File exists and overwrite is false")

        before = b""
        checkpoint_id: str | None = None
        if exists:
            try:
                before = target.read_bytes()
                checkpoint_id = self._create_checkpoint(target, before)
            except OSError as exc:
                return self._failure("checkpoint_failed", f"Unable to create checkpoint: {exc}")

        temporary: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(prefix=".netstudio-write-", dir=parent)
            temporary = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, target)
            temporary = None
        except OSError as exc:
            return self._failure("write_failed", f"Atomic write failed: {exc}")
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

        relative = target.relative_to(self._workspace_root).as_posix()
        operation = "overwritten" if exists else "created"
        before_text = before.decode("utf-8", errors="replace")
        diff = "".join(
            difflib.unified_diff(
                before_text.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
        diff_truncated = len(diff) > self._max_diff_chars
        if diff_truncated:
            diff = diff[: self._max_diff_chars]
        evidence = {
            "path": relative,
            "operation": operation,
            "bytes_written": len(encoded),
            "checkpoint_created": checkpoint_id is not None,
            "checkpoint_id": checkpoint_id,
            "diff": diff,
            "diff_truncated": diff_truncated,
        }
        return ToolResult(success=True, output=json.dumps(evidence, ensure_ascii=False), metadata=evidence)

    def _create_checkpoint(self, target: Path, content: bytes) -> str:
        checkpoint_id = uuid.uuid4().hex
        checkpoint_root = self._workspace_root / INTERNAL_DIRECTORY_NAME / "checkpoints"
        checkpoint_root.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_root / f"{checkpoint_id}.bin"
        metadata_path = checkpoint_root / f"{checkpoint_id}.json"
        checkpoint_path.write_bytes(content)
        metadata_path.write_text(
            json.dumps({"path": target.relative_to(self._workspace_root).as_posix()}),
            encoding="utf-8",
        )
        return checkpoint_id

    def _validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        unexpected = set(arguments) - {"path", "content", "create", "overwrite"}
        if unexpected:
            return f"Unsupported arguments: {', '.join(sorted(unexpected))}"
        if "path" not in arguments:
            return "path is required"
        if not isinstance(arguments["path"], str):
            return "path must be a string"
        if not arguments["path"].strip():
            return "path must not be empty"
        if "content" not in arguments:
            return "content is required"
        if not isinstance(arguments["content"], str):
            return "content must be a string"
        if not isinstance(arguments.get("create", False), bool):
            return "create must be a boolean"
        if not isinstance(arguments.get("overwrite", False), bool):
            return "overwrite must be a boolean"
        return None

    def _failure(self, code: str, message: str) -> ToolResult:
        return ToolResult(success=False, error=message, metadata={"code": code})
