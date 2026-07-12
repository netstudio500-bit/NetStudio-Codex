"""Tests for agent."""

import pytest

from netstudio.core.agent import Agent


class TestAgent:
    """Agent tests."""

    def test_agent_initialization(self) -> None:
        """Test agent initialization."""
        agent = Agent(name="test-agent")
        assert agent.name == "test-agent"
        assert agent.temperature == 0.7
        assert agent.max_tokens == 2048

    @pytest.mark.asyncio
    async def test_agent_execute(self) -> None:
        """Test agent execution."""
        agent = Agent(name="test-agent")
        result = await agent.execute("test task")
        assert result == "Executed: test task"

    @pytest.mark.asyncio
    async def test_agent_think(self) -> None:
        """Test agent thinking."""
        agent = Agent(name="test-agent")
        result = await agent.think("test context")
        assert result == "Thought about: test context"
