"""Behavior and integration tests for the production ShellTool."""

import asyncio
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.runtime import (
    AgentRuntime,
    DecisionKind,
    ExecutionContext,
    LLMDecisionSource,
    PolicySnapshot,
    RuntimeDecision,
    ScopeRef,
)
from netstudio.tools import (
    MAX_TIMEOUT_SECONDS,
    ShellTool,
    ToolCapability,
    ToolRegistry,
)


def python_command(script: str) -> str:
    """Build one command string parsed portably by ShellTool."""
    argv = [sys.executable, "-c", script]
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def context(workspace: Path, *capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        ScopeRef("test", workspace_root=workspace),
        PolicySnapshot(frozenset(capabilities)),
    )


class SequenceProvider(LLMProvider):
    """Deterministic provider returning structured decisions in sequence."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.requests: list[GenerationRequest] = []

    @property
    def name(self) -> str:
        return "sequence"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["sequence"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=next(self.responses), model="sequence")

    async def close(self) -> None:
        pass


class OneDecisionSource:
    def __init__(self, decision: RuntimeDecision) -> None:
        self.decision = decision

    async def decide(self, task: str, observations: tuple, iteration: int) -> RuntimeDecision:
        return self.decision


def test_shell_metadata_declares_capability_and_argument_schema(tmp_path: Path) -> None:
    metadata = ShellTool(tmp_path).metadata

    assert metadata.name == "shell"
    assert metadata.capabilities == frozenset({ToolCapability.LOCAL_EXECUTION})
    assert metadata.argument_schema["required"] == ["command"]
    assert metadata.argument_schema["additionalProperties"] is False
    properties = metadata.argument_schema["properties"]
    assert set(properties) == {"command", "timeout_seconds"}
    assert "cwd" not in properties
    assert properties["timeout_seconds"]["maximum"] == MAX_TIMEOUT_SECONDS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "command is required"),
        ({"command": 42}, "command must be a string"),
        ({"command": "   "}, "command must not be empty"),
        ({"command": "x", "timeout_seconds": 1.5}, "must be an integer"),
        ({"command": "x", "timeout_seconds": True}, "must be an integer"),
        ({"command": "x", "timeout_seconds": 0}, "greater than zero"),
        (
            {"command": "x", "timeout_seconds": MAX_TIMEOUT_SECONDS + 1},
            "must not exceed",
        ),
        ({"command": "x", "cwd": ".."}, "Unsupported arguments"),
    ],
)
async def test_shell_rejects_invalid_arguments(
    tmp_path: Path, arguments: dict, message: str
) -> None:
    result = await ShellTool(tmp_path).execute(arguments)

    assert result.success is False
    assert result.error is not None
    assert message in result.error


@pytest.mark.asyncio
async def test_shell_captures_stdout_stderr_and_zero_exit_code(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path).execute(
        {"command": python_command("import sys; print('OUT'); print('ERR', file=sys.stderr)")}
    )

    assert result.success is True
    assert result.output.strip() == "OUT"
    assert result.metadata["stderr"].strip() == "ERR"
    assert result.metadata["exit_code"] == 0
    assert result.metadata["timed_out"] is False


@pytest.mark.asyncio
async def test_shell_preserves_nonzero_exit_code_as_executed_result(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path).execute(
        {"command": python_command("import sys; print('bad', file=sys.stderr); sys.exit(7)")}
    )

    assert result.success is True
    assert result.metadata["exit_code"] == 7
    assert result.metadata["stderr"].strip() == "bad"


@pytest.mark.asyncio
async def test_shell_timeout_is_real_and_process_does_not_continue(tmp_path: Path) -> None:
    marker = tmp_path / "late.txt"
    script = (
        f"import time, pathlib; time.sleep(2); " f"pathlib.Path({str(marker)!r}).write_text('late')"
    )

    result = await ShellTool(tmp_path).execute(
        {"command": python_command(script), "timeout_seconds": 1}
    )
    await asyncio.sleep(1.5)

    assert result.success is False
    assert result.error == "Process timed out"
    assert result.metadata["timed_out"] is True
    assert result.metadata["exit_code"] is not None
    assert marker.exists() is False


@pytest.mark.asyncio
async def test_shell_bounds_stdout_and_marks_truncation(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path, output_limit_bytes=32).execute(
        {"command": python_command("print('A' * 200)")}
    )

    assert len(result.output.encode()) <= 32
    assert result.metadata["stdout_truncated"] is True
    assert result.metadata["stderr_truncated"] is False


@pytest.mark.asyncio
async def test_shell_bounds_stderr_and_marks_truncation(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path, output_limit_bytes=32).execute(
        {"command": python_command("import sys; print('E' * 200, file=sys.stderr)")}
    )

    assert len(result.metadata["stderr"].encode()) <= 32
    assert result.metadata["stderr_truncated"] is True
    assert result.metadata["stdout_truncated"] is False


@pytest.mark.asyncio
async def test_shell_cwd_is_fixed_to_authorized_workspace(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path).execute(
        {"command": python_command("import os; print(os.getcwd())")}
    )

    assert Path(result.output.strip()).resolve() == tmp_path.resolve()
    assert result.metadata["workspace_root"] == str(tmp_path.resolve())


def test_shell_is_absent_from_empty_policy_and_present_when_explicitly_allowed(
    tmp_path: Path,
) -> None:
    registry = ToolRegistry()
    registry.register(ShellTool(tmp_path))

    assert registry.view(context(tmp_path)).names() == ()
    assert registry.view(context(tmp_path, ToolCapability.LOCAL_EXECUTION)).names() == ("shell",)


@pytest.mark.asyncio
async def test_decision_prompt_hides_denied_shell_and_lists_permitted_shell(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(ShellTool(tmp_path))
    denied_provider = SequenceProvider(['{"action":"complete","content":"done"}'])
    allowed_provider = SequenceProvider(['{"action":"complete","content":"done"}'])

    denied_source = LLMDecisionSource(denied_provider, registry.view(context(tmp_path)))
    allowed_source = LLMDecisionSource(
        allowed_provider,
        registry.view(context(tmp_path, ToolCapability.LOCAL_EXECUTION)),
    )
    await denied_source.decide("task", (), 1)
    await allowed_source.decide("task", (), 1)

    assert "available_tools=[]" in denied_provider.requests[0].prompt
    assert '"name": "shell"' not in denied_provider.requests[0].prompt
    assert '"name": "shell"' in allowed_provider.requests[0].prompt
    assert '"command"' in allowed_provider.requests[0].prompt
    assert '"cwd"' not in allowed_provider.requests[0].prompt


@pytest.mark.asyncio
async def test_runtime_does_not_execute_shell_denied_by_empty_policy(tmp_path: Path) -> None:
    marker = tmp_path / "blocked.txt"
    registry = ToolRegistry()
    registry.register(ShellTool(tmp_path))
    decision = RuntimeDecision(
        DecisionKind.TOOL,
        "shell",
        {"command": python_command(f"from pathlib import Path; Path({str(marker)!r}).touch()")},
    )
    runtime = AgentRuntime(OneDecisionSource(decision), registry, context(tmp_path))

    result = await runtime.run("blocked")

    assert result.failure is not None
    assert result.failure.code == "tool_denied_or_missing"
    assert result.observations == ()
    assert marker.exists() is False


@pytest.mark.asyncio
async def test_agent_e2e_shell_observation_then_complete(tmp_path: Path) -> None:
    command = python_command("print('SHELL_OK')")
    provider = SequenceProvider(
        [
            json.dumps(
                {
                    "action": "tool",
                    "tool_name": "shell",
                    "arguments": {"command": command},
                }
            ),
            '{"action":"complete","content":"FINAL_OK"}',
        ]
    )
    agent = Agent(
        name="shell-agent",
        provider=provider,
        policy=PolicySnapshot(frozenset({ToolCapability.LOCAL_EXECUTION})),
        workspace_root=tmp_path,
    )

    result = await agent.execute("run portable command")

    assert result == "FINAL_OK"
    assert len(provider.requests) == 2
    assert '"name": "shell"' in provider.requests[0].prompt
    second_prompt = provider.requests[1].prompt
    assert "SHELL_OK" in second_prompt
    assert '"tool_name": "shell"' in second_prompt
    assert '"success": true' in second_prompt


@pytest.mark.asyncio
async def test_agent_default_policy_blocks_registered_shell(tmp_path: Path) -> None:
    command = python_command("print('SHOULD_NOT_RUN')")
    provider = SequenceProvider(
        [
            json.dumps(
                {
                    "action": "tool",
                    "tool_name": "shell",
                    "arguments": {"command": command},
                }
            )
        ]
    )
    agent = Agent(name="safe-agent", provider=provider, workspace_root=tmp_path)

    with pytest.raises(AgentRuntimeError) as error:
        await agent.execute("try shell")

    assert error.value.failure.code == "tool_denied_or_missing"
    assert "available_tools=[]" in provider.requests[0].prompt
