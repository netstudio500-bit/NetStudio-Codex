"""Integration tests for OllamaProvider."""

from collections.abc import AsyncIterator

import pytest

from netstudio.llm.base import GenerationRequest, GenerationResponse
from netstudio.llm.ollama import OllamaProvider


@pytest.fixture
async def ollama_provider() -> AsyncIterator[OllamaProvider]:
    """Create and validate an OllamaProvider fixture."""
    provider = OllamaProvider()

    try:
        is_healthy = await provider.health()
        if not is_healthy:
            pytest.skip("Ollama server not available")
    except ConnectionError as exc:
        pytest.skip(f"Ollama server not available: {exc}")

    try:
        yield provider
    finally:
        await provider.close()


@pytest.mark.asyncio
async def test_provider_name(ollama_provider: OllamaProvider) -> None:
    """Test that provider name is valid."""
    name = ollama_provider.name
    assert isinstance(name, str)
    assert name == "ollama"


@pytest.mark.asyncio
async def test_provider_health(ollama_provider: OllamaProvider) -> None:
    """Test health check functionality."""
    health = await ollama_provider.health()
    assert isinstance(health, bool)
    assert health is True


@pytest.mark.asyncio
async def test_list_models(ollama_provider: OllamaProvider) -> None:
    """Test model listing functionality."""
    models = await ollama_provider.list_models()
    assert isinstance(models, list)
    assert len(models) >= 1
    assert all(isinstance(model, str) for model in models)


@pytest.mark.asyncio
async def test_generate(ollama_provider: OllamaProvider) -> None:
    """Test text generation functionality."""
    request = GenerationRequest(prompt="Responda apenas: OK")
    response = await ollama_provider.generate(request)

    assert isinstance(response, GenerationResponse)
    assert isinstance(response.text, str)
    assert response.text
    assert isinstance(response.model, str)
    assert response.model


@pytest.mark.asyncio
async def test_multiple_generate(ollama_provider: OllamaProvider) -> None:
    """Test multiple consecutive generation calls."""
    request1 = GenerationRequest(prompt="Test 1")
    response1 = await ollama_provider.generate(request1)
    assert isinstance(response1, GenerationResponse)
    assert response1.text

    request2 = GenerationRequest(prompt="Test 2")
    response2 = await ollama_provider.generate(request2)
    assert isinstance(response2, GenerationResponse)
    assert response2.text


@pytest.mark.asyncio
async def test_close() -> None:
    """Test provider cleanup independently."""
    provider = OllamaProvider()
    await provider.close()
