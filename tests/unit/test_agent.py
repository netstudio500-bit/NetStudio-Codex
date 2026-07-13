"""Tests for Agent and its operational AgentRuntime integration."""

import pytest

from netstudio.core.agent import Agent, AgentRuntimeError
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic provider used to verify agent/runtime/provider integration."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = iter(responses or ['{"action":"complete","content":"done"}'])
        self.requests: list[GenerationRequest] = []
        self.closed = False

    @property
    def name(self) -> str:
        return "fake"

    async def health(self) -> bool:
        return True

    async def list_models(self) -> list[str]:
        return ["fake-model"]

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.requests.append(request)
        return GenerationResponse(text=next(self.responses), model="fake-model")

    async def close(self) -> None:
        self.closed = True


class TestAgent:
    """Agent tests."""

    def test_agent_initialization(self) -> None:
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)

        assert agent.name == "test-agent"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_agent_execute_crosses_runtime_decision_source_and_provider(
        self,
    ) -> None:
        provider = FakeProvider(['{"action":"complete","content":"runtime result"}'])
        agent = Agent(name="test-agent", system_prompt="Be useful", provider=provider)

        result = await agent.execute("test task")

        assert result == "runtime result"
        assert len(provider.requests) == 1
        assert 'task="test task"' in provider.requests[0].prompt
        assert "available_tools=[]" in provider.requests[0].prompt
        assert provider.requests[0].system_prompt == "Be useful"

    @pytest.mark.asyncio
    async def test_agent_empty_registry_can_complete(self) -> None:
        provider = FakeProvider(['{"action":"complete","content":"OK"}'])
        agent = Agent(name="test-agent", provider=provider)

        assert await agent.execute("finish without tools") == "OK"

    @pytest.mark.asyncio
    async def test_agent_propagates_invalid_provider_decision_as_runtime_failure(
        self,
    ) -> None:
        provider = FakeProvider(["arbitrary text"])
        agent = Agent(name="test-agent", provider=provider)

        with pytest.raises(AgentRuntimeError) as error:
            await agent.execute("invalid")

        assert error.value.failure.code == "runtime_error"
        assert "Invalid decision JSON" in error.value.failure.message
        assert error.value.failure.iteration == 1

    @pytest.mark.asyncio
    async def test_agent_fails_when_model_requests_missing_tool(self) -> None:
        provider = FakeProvider(
            ['{"action":"tool","tool_name":"missing","arguments":{}}']
        )
        agent = Agent(name="test-agent", provider=provider)

        with pytest.raises(AgentRuntimeError) as error:
            await agent.execute("use missing tool")

        assert error.value.failure.code == "tool_denied_or_missing"
        assert "missing" in error.value.failure.message

    @pytest.mark.asyncio
    async def test_agent_memory_is_added_to_decision_context(self) -> None:
        provider = FakeProvider(['{"action":"complete","content":"continued"}'])
        agent = Agent(name="test-agent", provider=provider)

        await agent.remember("project uses Python")
        await agent.execute("continue")

        assert "project uses Python" in provider.requests[0].prompt
        assert 'task="continue"' in provider.requests[0].prompt

    @pytest.mark.asyncio
    async def test_agent_think_uses_provider_directly_as_non_task_api(self) -> None:
        provider = FakeProvider(["analysis"])
        agent = Agent(name="test-agent", provider=provider)

        result = await agent.think("test context")

        assert result == "analysis"
        assert provider.requests[0].prompt.startswith("Analise o contexto")

    @pytest.mark.asyncio
    async def test_agent_close_closes_provider(self) -> None:
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)

        await agent.close()

        assert provider.closed is True
