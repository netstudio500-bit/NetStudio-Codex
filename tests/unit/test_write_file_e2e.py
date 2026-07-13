"""Real CLI/runtime E2E coverage for write_file."""

import json
from pathlib import Path
from typing import Any

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.main import build_parser, main
from netstudio.runtime import PolicySnapshot
from netstudio.runtime.capabilities import ToolCapability


class WriteFlowProvider(LLMProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.requests: list[GenerationRequest] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "write-flow"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["fake"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=next(self.responses), model="fake")

    async def close(self) -> None:
        self.closed = True


def decision(tool: str, arguments: dict[str, Any]) -> str:
    return json.dumps({"action": "tool", "tool_name": tool, "arguments": arguments})


def install(monkeypatch, provider: LLMProvider, captured: dict[str, Any]) -> None:
    def factory(**kwargs: Any) -> Agent:
        captured.update(kwargs)
        return Agent(provider=provider, **kwargs)
    monkeypatch.setattr("netstudio.main.Agent", factory)


@pytest.mark.asyncio
async def test_cli_discover_read_write_read_complete(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "src"
    source.mkdir()
    target = source / "target.txt"
    target.write_text("OLD_VALUE", encoding="utf-8")
    provider = WriteFlowProvider([
        decision("search_text", {"query": "OLD_VALUE"}),
        decision("read_file", {"path": "src/target.txt"}),
        decision("write_file", {"path": "src/target.txt", "content": "NEW_VALUE", "overwrite": True}),
        decision("read_file", {"path": "src/target.txt"}),
        json.dumps({"action": "complete", "content": "WRITE FLOW OK"}),
    ])
    captured: dict[str, Any] = {}
    install(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    await main(build_parser().parse_args(["modify target", "--allow-read", "--allow-write"]))
    assert target.read_text(encoding="utf-8") == "NEW_VALUE"
    assert captured["policy"] == PolicySnapshot(frozenset({ToolCapability.READ, ToolCapability.WRITE}))
    assert "src/target.txt" in provider.requests[1].prompt
    assert "OLD_VALUE" in provider.requests[2].prompt
    assert '"operation": "overwritten"' in provider.requests[3].prompt
    assert "OLD_VALUE" in provider.requests[3].prompt and "NEW_VALUE" in provider.requests[3].prompt
    assert "NEW_VALUE" in provider.requests[4].prompt
    assert "WRITE FLOW OK" in capsys.readouterr().out
    assert provider.closed is True


@pytest.mark.asyncio
async def test_cli_read_without_write_blocks_mutation_and_checkpoint(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "target.txt"
    original = b"ORIGINAL_BYTES"
    target.write_bytes(original)
    provider = WriteFlowProvider([
        decision("read_file", {"path": "target.txt"}),
        decision("write_file", {"path": "target.txt", "content": "MUTATED", "overwrite": True}),
    ])
    captured: dict[str, Any] = {}
    install(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AgentRuntimeError) as error:
        await main(build_parser().parse_args(["mutate", "--allow-read"]))
    assert error.value.failure.code == "tool_denied_or_missing"
    assert target.read_bytes() == original
    assert not (tmp_path / ".netstudio").exists()
    assert '"name": "write_file"' not in provider.requests[0].prompt
    assert provider.closed is True
