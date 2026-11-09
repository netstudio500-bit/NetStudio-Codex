"""Real CLI/runtime E2E coverage for list_files discovery."""

import json
from pathlib import Path
from typing import Any

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.main import build_parser, main
from netstudio.runtime import PolicySnapshot
from netstudio.runtime.capabilities import ToolCapability


class DiscoveryProvider(LLMProvider):
    """Deterministic provider driving list, read, then complete decisions."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.requests: list[GenerationRequest] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "discovery-provider"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["discovery-model"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=next(self.responses), model="discovery-model")

    async def close(self) -> None:
        self.closed = True


def decision(tool_name: str, arguments: dict[str, Any]) -> str:
    return json.dumps({"action": "tool", "tool_name": tool_name, "arguments": arguments})


def install_real_agent(
    monkeypatch: pytest.MonkeyPatch,
    provider: LLMProvider,
    captured: dict[str, Any],
) -> None:
    """Inject only the provider while preserving the real Agent and runtime."""

    def factory(**kwargs: Any) -> Agent:
        captured.update(kwargs)
        return Agent(provider=provider, **kwargs)

    monkeypatch.setattr("netstudio.main.Agent", factory)


@pytest.mark.asyncio
async def test_cli_allow_read_lists_discovers_reads_and_completes(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    (tmp_path / "README.txt").write_text("README", encoding="utf-8")
    source = tmp_path / "src"
    source.mkdir()
    (source / "module.txt").write_text("DISCOVERED_FILE_OK", encoding="utf-8")
    provider = DiscoveryProvider(
        [
            decision("list_files", {"path": ".", "recursive": True}),
            decision("read_file", {"path": "src/module.txt"}),
            json.dumps({"action": "complete", "content": "DISCOVERY COMPLETE"}),
        ]
    )
    captured: dict[str, Any] = {}
    install_real_agent(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["discover and read", "--allow-read"])

    await main(args)

    output = capsys.readouterr().out
    assert captured["policy"] == PolicySnapshot(frozenset({ToolCapability.READ}))
    assert captured["workspace_root"] == tmp_path.resolve()
    assert "Workspace file reading authorized." in output
    assert "DISCOVERY COMPLETE" in output
    assert '"name": "list_files"' in provider.requests[0].prompt
    assert '"name": "read_file"' in provider.requests[0].prompt
    assert '"name": "shell"' not in provider.requests[0].prompt
    assert '"default": "."' in provider.requests[0].prompt
    assert '"default": false' in provider.requests[0].prompt
    assert "src/module.txt" in provider.requests[1].prompt
    assert '"tool_name": "list_files"' in provider.requests[1].prompt
    assert '"truncated": false' in provider.requests[1].prompt
    assert "DISCOVERED_FILE_OK" in provider.requests[2].prompt
    assert '"tool_name": "read_file"' in provider.requests[2].prompt
    assert '"path": "src/module.txt"' in provider.requests[2].prompt
    assert len(provider.requests) == 3
    assert provider.closed is True


@pytest.mark.asyncio
async def test_cli_without_read_blocks_list_files_before_observation(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "PRIVATE_WORKSPACE_NAME.txt").write_text("PRIVATE_CONTENT", encoding="utf-8")
    provider = DiscoveryProvider(
        [
            decision("list_files", {"path": ".", "recursive": True}),
            json.dumps({"action": "complete", "content": "must not run"}),
        ]
    )
    captured: dict[str, Any] = {}
    install_real_agent(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["discover workspace"])

    with pytest.raises(AgentRuntimeError) as error:
        await main(args)

    assert error.value.failure.code == "tool_denied_or_missing"
    assert captured["policy"].allowed_capabilities == frozenset()
    assert len(provider.requests) == 1
    assert "available_tools=[]" in provider.requests[0].prompt
    assert '"name": "list_files"' not in provider.requests[0].prompt
    assert '"name": "read_file"' not in provider.requests[0].prompt
    assert "PRIVATE_WORKSPACE_NAME.txt" not in provider.requests[0].prompt
    assert "PRIVATE_CONTENT" not in provider.requests[0].prompt
    assert provider.closed is True


@pytest.mark.asyncio
async def test_local_execution_prompt_hides_both_read_tools(tmp_path: Path, monkeypatch) -> None:
    provider = DiscoveryProvider([json.dumps({"action": "complete", "content": "LOCAL ONLY"})])
    captured: dict[str, Any] = {}
    install_real_agent(monkeypatch, provider, captured)
    monkeypatch.chdir(tmp_path)
    args = build_parser().parse_args(["inspect tools", "--allow-local-execution"])

    await main(args)

    prompt = provider.requests[0].prompt
    assert '"name": "shell"' in prompt
    assert '"name": "list_files"' not in prompt
    assert '"name": "read_file"' not in prompt
