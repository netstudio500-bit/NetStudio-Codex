"""Tests for agent."""

import pytest

from netstudio.core.agent import Agent
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider


class FakeProvider(LLMProvider):
    """Deterministic provider used to verify agent/provider integration."""

    def __init__(self) -> None:
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
        return GenerationResponse(text=f"LLM: {request.prompt}", model="fake-model")

    async def close(self) -> None:
        self.closed = True


class TestAgent:
    """Agent tests."""

    def test_agent_initialization(self) -> None:
        """Test agent initialization."""
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)
        assert agent.name == "test-agent"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_agent_execute_uses_provider(self) -> None:
        """Agent execution must call the configured LLM provider."""
        provider = FakeProvider()
        agent = Agent(name="test-agent", system_prompt="Be useful", provider=provider)

        result = await agent.execute("test task")

        assert result == "LLM: test task"
        assert len(provider.requests) == 1
        assert provider.requests[0].prompt == "test task"
        assert provider.requests[0].system_prompt == "Be useful"

    @pytest.mark.asyncio
    async def test_agent_think_uses_provider(self) -> None:
        """Agent analysis must call the configured LLM provider."""
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)

        result = await agent.think("test context")

        assert result.startswith("LLM: Analise o contexto")
        assert "test context" in provider.requests[0].prompt

    @pytest.mark.asyncio
    async def test_agent_memory_is_added_to_execution_context(self) -> None:
        """Recent session memory is injected into the next execution."""
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)

        await agent.remember("project uses Python")
        await agent.execute("continue")

        assert "project uses Python" in provider.requests[0].prompt
        assert "continue" in provider.requests[0].prompt

    @pytest.mark.asyncio
    async def test_agent_close_closes_provider(self) -> None:
        """Agent cleanup delegates to its provider."""
        provider = FakeProvider()
        agent = Agent(name="test-agent", provider=provider)

        await agent.close()

        assert provider.closed is True
