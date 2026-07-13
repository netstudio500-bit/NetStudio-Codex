"""Tests for the operational CLI path."""

from argparse import Namespace

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.main import build_parser, execute_task, interactive


class FakeAgent:
    """Minimal agent double for CLI orchestration tests."""

    def __init__(
        self,
        execution_error: Exception | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.tasks: list[str] = []
        self.memories: list[str] = []
        self.closed = False
        self.execution_error = execution_error
        self.close_error = close_error

    async def execute(self, task: str) -> str:
        self.tasks.append(task)
        if self.execution_error is not None:
            raise self.execution_error
        return f"result: {task}"

    async def remember(self, memory: str) -> None:
        self.memories.append(memory)

    async def close(self) -> None:
        self.closed = True
        if self.close_error is not None:
            raise self.close_error


class RuntimeProvider(LLMProvider):
    """Deterministic provider proving CLI task execution reaches runtime decisions."""

    def __init__(self, response: str) -> None:
        self.response = response
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
        return GenerationResponse(text=self.response, model="runtime-model")

    async def close(self) -> None:
        self.closed = True


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
async def test_execute_task_propagates_cleanup_failure() -> None:
    agent = FakeAgent(close_error=RuntimeError("cleanup failed"))

    with pytest.raises(RuntimeError, match="cleanup failed"):
        await execute_task(agent, "work")

    assert agent.closed is True


@pytest.mark.asyncio
async def test_execute_task_preserves_operation_and_cleanup_failures() -> None:
    agent = FakeAgent(
        execution_error=ValueError("execution failed"),
        close_error=RuntimeError("cleanup failed"),
    )

    with pytest.raises(ExceptionGroup) as error:
        await execute_task(agent, "work")

    assert [str(exc) for exc in error.value.exceptions] == [
        "execution failed",
        "cleanup failed",
    ]
    assert agent.closed is True


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


def test_parser_accepts_task_model_and_interactive_mode() -> None:
    parser = build_parser()

    task_args: Namespace = parser.parse_args(["do work", "--model", "qwen3"])
    interactive_args: Namespace = parser.parse_args(["--interactive"])

    assert task_args.task == "do work"
    assert task_args.model == "qwen3"
    assert task_args.interactive is False
    assert interactive_args.interactive is True
