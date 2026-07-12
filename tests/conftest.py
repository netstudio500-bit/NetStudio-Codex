"""Pytest configuration and fixtures."""

import pytest

from netstudio.core.agent import Agent
from netstudio.core.config import Config


@pytest.fixture
def config():
    """Provide test configuration."""
    return Config(app_env="testing", debug=True)


@pytest.fixture
def agent():
    """Provide test agent."""
    return Agent(name="test-agent", description="A test agent")
