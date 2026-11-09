"""Policy-gated local process execution constrained to one workspace."""

import asyncio
import os
import shlex
import signal
from pathlib import Path
from typing import Any

from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools.base import Tool, ToolMetadata, ToolResult

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
DEFAULT_OUTPUT_LIMIT_BYTES = 64 * 1024
_READ_CHUNK_BYTES = 4096
_CREATE_NEW_PROCESS_GROUP = 0x00000200


class ShellTool(Tool):
    """Execute one argv command without implicit shell interpretation."""

    def __init__(
        self,
        workspace_root: Path,
        output_limit_bytes: int = DEFAULT_OUTPUT_LIMIT_BYTES,
    ) -> None:
        if output_limit_bytes <= 0:
            raise ValueError("output_limit_bytes must be greater than zero")
        self._workspace_root = workspace_root.resolve(strict=True)
        if not self._workspace_root.is_dir():
            raise ValueError("workspace_root must be a directory")
        self._output_limit_bytes = output_limit_bytes

    @property
    def metadata(self) -> ToolMetadata:
        """Declare the shell contract and LOCAL_EXECUTION capability."""
        return ToolMetadata(
            name="shell",
            description=(
                "Execute one local command in the authorized workspace without shell syntax"
            ),
            capabilities=frozenset({ToolCapability.LOCAL_EXECUTION}),
            argument_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "minLength": 1},
                    "timeout_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TIMEOUT_SECONDS,
                        "default": DEFAULT_TIMEOUT_SECONDS,
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Validate arguments, execute the process and return bounded output."""
        validation_error = self._validate_arguments(arguments)
        if validation_error is not None:
            return ToolResult(success=False, error=validation_error)

        command = arguments["command"]
        timeout_seconds = arguments.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        try:
            argv = self._split_command(command)
        except ValueError as exc:
            return ToolResult(success=False, error=f"Invalid command syntax: {exc}")
        if not argv:
            return ToolResult(success=False, error="command must not be empty")

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                cwd=str(self._workspace_root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **self._process_group_options(),
            )
        except (OSError, ValueError) as exc:
            return ToolResult(
                success=False,
                error=f"Process start failed: {exc}",
                metadata={"start_failed": True},
            )

        stdout_task = asyncio.create_task(self._read_bounded(process.stdout))
        stderr_task = asyncio.create_task(self._read_bounded(process.stderr))
        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout=timeout_seconds)
        except TimeoutError:
            timed_out = True
            await self._terminate_process_tree(process)

        stdout_data, stdout_truncated = await stdout_task
        stderr_data, stderr_truncated = await stderr_task
        metadata = {
            "exit_code": process.returncode,
            "timed_out": timed_out,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "workspace_root": str(self._workspace_root),
        }
        if timed_out:
            return ToolResult(
                success=False,
                output=stdout_data,
                error="Process timed out",
                metadata={**metadata, "stderr": stderr_data},
            )
        return ToolResult(
            success=True,
            output=stdout_data,
            metadata={**metadata, "stderr": stderr_data},
        )

    def _validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        allowed = {"command", "timeout_seconds"}
        unexpected = set(arguments) - allowed
        if unexpected:
            return f"Unsupported arguments: {', '.join(sorted(unexpected))}"
        if "command" not in arguments:
            return "command is required"
        command = arguments["command"]
        if not isinstance(command, str):
            return "command must be a string"
        if not command.strip():
            return "command must not be empty"
        timeout = arguments.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            return "timeout_seconds must be an integer"
        if timeout <= 0:
            return "timeout_seconds must be greater than zero"
        if timeout > MAX_TIMEOUT_SECONDS:
            return f"timeout_seconds must not exceed {MAX_TIMEOUT_SECONDS}"
        return None

    def _split_command(self, command: str) -> list[str]:
        if os.name != "nt":
            return shlex.split(command, posix=True)
        tokens = shlex.split(command, posix=False)
        return [
            token[1:-1]
            if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}
            else token
            for token in tokens
        ]

    async def _read_bounded(self, stream: asyncio.StreamReader | None) -> tuple[str, bool]:
        if stream is None:
            return "", False
        captured = bytearray()
        truncated = False
        while True:
            chunk = await stream.read(_READ_CHUNK_BYTES)
            if not chunk:
                break
            remaining = self._output_limit_bytes - len(captured)
            if remaining > 0:
                captured.extend(chunk[:remaining])
            if len(chunk) > remaining:
                truncated = True
        return captured.decode(errors="replace"), truncated

    def _process_group_options(self) -> dict[str, Any]:
        if os.name == "nt":
            return {"creationflags": _CREATE_NEW_PROCESS_GROUP}
        return {"start_new_session": True}

    async def _terminate_process_tree(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        if os.name == "nt":
            try:
                killer = await asyncio.create_subprocess_exec(
                    "taskkill",
                    "/PID",
                    str(process.pid),
                    "/T",
                    "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                taskkill_exit_code = await killer.wait()
            except OSError as exc:
                process.kill()
                await process.wait()
                raise RuntimeError(f"Failed to start taskkill: {exc}") from exc
            if taskkill_exit_code != 0:
                process.kill()
                await process.wait()
                raise RuntimeError(f"taskkill failed with exit code {taskkill_exit_code}")
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.returncode is None:
            process.kill()
        await process.wait()
