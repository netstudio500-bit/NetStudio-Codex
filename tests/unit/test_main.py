"""Tests for the operational CLI path."""

from argparse import Namespace

import pytest

from netstudio.main import build_parser, execute_task, interactive


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


@pytest.mark.asyncio
async def test_execute_task_runs_agent_and_closes_it() -> None:
    agent = FakeAgent()

    result = await execute_task(agent, "inspect repository")  # type: ignore[arg-type]

    assert result == "result: inspect repository"
    assert agent.tasks == ["inspect repository"]
    assert agent.closed is True


@pytest.mark.asyncio
async def test_execute_task_closes_agent_after_failure() -> None:
    class FailingAgent(FakeAgent):
        async def execute(self, task: str) -> str:
            raise RuntimeError("provider failed")

    agent = FailingAgent()

    with pytest.raises(RuntimeError, match="provider failed"):
        await execute_task(agent, "fail")  # type: ignore[arg-type]

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


def test_parser_accepts_task_model_and_interactive_mode() -> None:
    parser = build_parser()

    task_args: Namespace = parser.parse_args(["do work", "--model", "qwen3"])
    interactive_args: Namespace = parser.parse_args(["--interactive"])

    assert task_args.task == "do work"
    assert task_args.model == "qwen3"
    assert task_args.interactive is False
    assert interactive_args.interactive is True
