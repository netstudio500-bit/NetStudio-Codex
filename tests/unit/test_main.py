"""Tests for the operational CLI path."""

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.main import build_parser, build_policy, execute_task, interactive, main
from netstudio.runtime import PolicySnapshot
from netstudio.runtime.capabilities import ToolCapability


class FakeAgent:
    """Minimal agent double for CLI orchestration tests."""

    def __init__(self) -> None:
        self.tasks: list[str] = []
        self.memories: list[str] = []
        self.closed = False

    async def execute(self, task: str) -> str:
        self.tasks.append(task)
        return f"result: {task}"

    async def remember(self, memory: str) -> None:
        self.memories.append(memory)

    async def close(self) -> None:
        self.closed = True


class RuntimeProvider(LLMProvider):
    """Deterministic provider proving CLI execution reaches runtime decisions."""

    def __init__(self, responses: str | list[str]) -> None:
        values = [responses] if isinstance(responses, str) else responses
        self.responses = iter(values)
        self.requests: list[GenerationRequest] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "runtime-provider"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["runtime-model"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=next(self.responses), model="runtime-model")

    async def close(self) -> None:
        self.closed = True


def python_command(script: str) -> str:
    """Build a portable command string for ShellTool."""
    argv = [sys.executable, "-c", script]
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def shell_responses(command: str, final: str = "CLI SHELL OK") -> list[str]:
    """Return the tool then complete decisions for a deterministic provider."""
    return [
        json.dumps(
            {
                "action": "tool",
                "tool_name": "shell",
                "arguments": {"command": command},
            }
        ),
        json.dumps({"action": "complete", "content": final}),
    ]


def install_real_agent_factory(
    monkeypatch: pytest.MonkeyPatch,
    provider: LLMProvider,
    captured: dict[str, Any],
) -> None:
    """Keep CLI construction real except for injecting a deterministic provider."""

    def factory(**kwargs: Any) -> Agent:
        captured.update(kwargs)
        return Agent(provider=provider, **kwargs)

    monkeypatch.setattr("netstudio.main.Agent", factory)


@pytest.mark.asyncio
async def test_execute_task_direct_cli_path_crosses_agent_runtime_and_closes_provider() -> None:
    provider = RuntimeProvider('{"action":"complete","content":"CLI OK"}')
    agent = Agent(name="cli-agent", provider=provider)

    result = await execute_task(agent, "inspect repository")

    assert result == "CLI OK"
    assert 'task="inspect repository"' in provider.requests[0].prompt
    assert provider.closed is True


@pytest.mark.asyncio
async def test_execute_task_closes_provider_after_runtime_failure() -> None:
    provider = RuntimeProvider("invalid provider response")
    agent = Agent(name="cli-agent", provider=provider)

    with pytest.raises(AgentRuntimeError, match="runtime_error"):
        await execute_task(agent, "fail")

    assert provider.closed is True


@pytest.mark.asyncio
async def test_interactive_executes_and_remembers_turn(monkeypatch, capsys) -> None:
    agent = FakeAgent()
    inputs = iter(["first task", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    await interactive(agent)  # type: ignore[arg-type]

    assert agent.tasks == ["first task"]
    assert agent.memories == ["Tarefa: first task\nResposta: result: first task"]
    assert agent.closed is True
    assert "result: first task" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_interactive_real_agent_uses_runtime_and_closes_provider(monkeypatch, capsys) -> None:
    provider = RuntimeProvider('{"action":"complete","content":"interactive OK"}')
    agent = Agent(name="cli-agent", provider=provider)
    inputs = iter(["first task", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    await interactive(agent)

    assert 'task="first task"' in provider.requests[0].prompt
    assert provider.closed is True
    assert "interactive OK" in capsys.readouterr().out


def test_parser_accepts_local_execution_flag() -> None:
    args = build_parser().parse_args(["do work", "--allow-local-execution"])

    assert args.allow_local_execution is True


def test_cli_policy_is_empty_without_flag() -> None:
    args = build_parser().parse_args(["do work"])

    assert build_policy(args).allowed_capabilities == frozenset()


def test_cli_policy_grants_only_local_execution_with_flag() -> None:
    args = build_parser().parse_args(["do work", "--allow-local-execution"])

    assert build_policy(args).allowed_capabilities == frozenset(
        {ToolCapability.LOCAL_EXECUTION}
    )


def test_help_documents_workspace_scoped_local_execution(capsys) -> None:
    with pytest.raises(SystemExit) as exit_info:
        build_parser().parse_args(["--help"])

    help_text = capsys.readouterr().out
    normalized_help = " ".join(help_text.split())
    assert exit_info.value.code == 0
    assert "--allow-local-execution" in help_text
    assert "inside the authorized workspace" in normalized_help
    assert "unrestricted" not in help_text.lower()
    assert "sandbox" not in help_text.lower()


@pytest.mark.asyncio
async def test_cli_without_flag_blocks_shell_and_does_not_execute_process(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    marker = tmp_path / "blocked.txt"
    command = python_command(f"from pathlib import Path; Path({str(marker)!r}).touch()")
    provider = RuntimeProvider(shell_responses(command))
    captured: dict[str, Any] = {}
    install_real_agent_factory(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["try shell"])

    with pytest.raises(AgentRuntimeError) as error:
        await main(args)

    assert error.value.failure.code == "tool_denied_or_missing"
    assert marker.exists() is False
    assert captured["policy"].allowed_capabilities == frozenset()
    assert captured["workspace_root"] == tmp_path.resolve()
    assert "available_tools=[]" in provider.requests[0].prompt
    assert "Local process execution authorized" not in capsys.readouterr().out
    assert provider.closed is True


@pytest.mark.asyncio
async def test_cli_with_flag_runs_shell_in_workspace_and_completes(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    marker = tmp_path / "executed.txt"
    script = (
        "from pathlib import Path; import os; "
        f"Path({str(marker)!r}).write_text(os.getcwd()); print('CLI_PROCESS_OK')"
    )
    provider = RuntimeProvider(shell_responses(python_command(script)))
    captured: dict[str, Any] = {}
    install_real_agent_factory(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["run shell", "--allow-local-execution"])

    await main(args)

    output = capsys.readouterr().out
    assert captured["policy"] == PolicySnapshot(
        frozenset({ToolCapability.LOCAL_EXECUTION})
    )
    assert captured["workspace_root"] == tmp_path.resolve()
    assert marker.read_text() == str(tmp_path.resolve())
    assert "Local process execution authorized for this workspace." in output
    assert "CLI SHELL OK" in output
    assert '"name": "shell"' in provider.requests[0].prompt
    assert "CLI_PROCESS_OK" in provider.requests[1].prompt
    assert '"tool_name": "shell"' in provider.requests[1].prompt
    assert '"success": true' in provider.requests[1].prompt
    assert provider.closed is True


@pytest.mark.asyncio
async def test_interactive_cli_preserves_explicit_policy_for_session(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    provider = RuntimeProvider(
        shell_responses(
            python_command("print('INTERACTIVE_SHELL_OK')"), "INTERACTIVE DONE"
        )
    )
    captured: dict[str, Any] = {}
    install_real_agent_factory(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    inputs = iter(["run shell", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    args = build_parser().parse_args(["--interactive", "--allow-local-execution"])

    await main(args)

    output = capsys.readouterr().out
    assert captured["policy"].allowed_capabilities == frozenset(
        {ToolCapability.LOCAL_EXECUTION}
    )
    assert len(provider.requests) == 2
    assert '"name": "shell"' in provider.requests[0].prompt
    assert "INTERACTIVE_SHELL_OK" in provider.requests[1].prompt
    assert "INTERACTIVE DONE" in output
    assert provider.closed is True
