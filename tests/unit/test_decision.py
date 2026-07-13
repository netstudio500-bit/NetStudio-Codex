"""Tests for the strict LLM RuntimeDecision protocol."""

from typing import Any

import pytest

from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider
from netstudio.runtime import (
    DecisionKind,
    DecisionParseError,
    ExecutionContext,
    LLMDecisionSource,
    PolicySnapshot,
    ScopeRef,
    parse_runtime_decision,
)
from netstudio.tools import Tool, ToolCapability, ToolMetadata, ToolRegistry, ToolResult


class StaticProvider(LLMProvider):
    """Provider returning one deterministic decision response."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.requests: list[GenerationRequest] = []

    @property
    def name(self) -> str:
        return "static"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["static"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=self.text, model="static")

    async def close(self) -> None:
        pass


class ReadTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="reader",
            description="Read one named value",
            capabilities=frozenset({ToolCapability.READ}),
            argument_schema={"name": "string"},
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, output=str(arguments["name"]))


def test_parse_valid_complete_json() -> None:
    decision = parse_runtime_decision('{"action":"complete","content":"OK"}')

    assert decision.kind is DecisionKind.COMPLETE
    assert decision.output == "OK"


def test_parse_valid_tool_json() -> None:
    decision = parse_runtime_decision(
        '{"action":"tool","tool_name":"reader","arguments":{"name":"x"}}'
    )

    assert decision.kind is DecisionKind.TOOL
    assert decision.tool_name == "reader"
    assert decision.arguments == {"name": "x"}


def test_parse_invalid_json() -> None:
    with pytest.raises(DecisionParseError, match="Invalid decision JSON"):
        parse_runtime_decision("not json")


def test_parse_unknown_action() -> None:
    with pytest.raises(DecisionParseError, match="Unknown decision action"):
        parse_runtime_decision('{"action":"invent"}')


def test_parse_tool_without_name() -> None:
    with pytest.raises(DecisionParseError, match="non-empty tool_name"):
        parse_runtime_decision('{"action":"tool","arguments":{}}')


def test_parse_tool_with_invalid_arguments() -> None:
    with pytest.raises(DecisionParseError, match="arguments must be a JSON object"):
        parse_runtime_decision('{"action":"tool","tool_name":"reader","arguments":[]}')


@pytest.mark.asyncio
async def test_decision_source_rejects_invalid_provider_decision() -> None:
    provider = StaticProvider("plain text")
    registry = ToolRegistry()
    source = LLMDecisionSource(
        provider,
        registry.view(ExecutionContext(ScopeRef("test"), PolicySnapshot())),
    )

    with pytest.raises(DecisionParseError, match="Invalid decision JSON"):
        await source.decide("task", (), 1)


@pytest.mark.asyncio
async def test_decision_prompt_lists_only_permitted_tools_and_contracts() -> None:
    provider = StaticProvider('{"action":"complete","content":"done"}')
    registry = ToolRegistry()
    registry.register(ReadTool())
    permitted_context = ExecutionContext(
        ScopeRef("test"), PolicySnapshot(frozenset({ToolCapability.READ}))
    )
    source = LLMDecisionSource(provider, registry.view(permitted_context))

    await source.decide("inspect", (), 1)

    prompt = provider.requests[0].prompt
    assert '"name": "reader"' in prompt
    assert '"argument_schema": {"name": "string"}' in prompt
    assert "write" not in prompt
