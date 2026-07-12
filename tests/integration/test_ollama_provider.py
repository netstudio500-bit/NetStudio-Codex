"""Integration tests for OllamaProvider."""

import pytest

from netstudio.llm.base import GenerationRequest, GenerationResponse
from netstudio.llm.ollama import OllamaProvider


@pytest.fixture
async def ollama_provider() -> OllamaProvider:
    """Create and validate OllamaProvider fixture.

    Yields:
        OllamaProvider: Configured provider instance.

    Skips:
        If Ollama server is not available.
    """
    provider = OllamaProvider()

    try:
        is_healthy = await provider.health()
        if not is_healthy:
            pytest.skip("Ollama server not available")
    except Exception as e:
        pytest.skip(f"Ollama server not available: {e}")

    yield provider

    await provider.close()


@pytest.mark.asyncio
async def test_provider_name(ollama_provider: OllamaProvider) -> None:
    """Test that provider name is valid.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    name = ollama_provider.name
    assert isinstance(name, str)
    assert len(name) > 0
    assert name == "ollama"


@pytest.mark.asyncio
async def test_provider_health(ollama_provider: OllamaProvider) -> None:
    """Test health check functionality.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    health = await ollama_provider.health()
    assert isinstance(health, bool)
    assert health is True


@pytest.mark.asyncio
async def test_list_models(ollama_provider: OllamaProvider) -> None:
    """Test model listing functionality.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    models = await ollama_provider.list_models()
    assert isinstance(models, list)
    assert len(models) >= 1
    assert all(isinstance(m, str) for m in models)


@pytest.mark.asyncio
async def test_generate(ollama_provider: OllamaProvider) -> None:
    """Test text generation functionality.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    request = GenerationRequest(prompt="Responda apenas: OK")
    response = await ollama_provider.generate(request)

    assert isinstance(response, GenerationResponse)
    assert isinstance(response.text, str)
    assert len(response.text) > 0
    assert isinstance(response.model, str)
    assert len(response.model) > 0


@pytest.mark.asyncio
async def test_multiple_generate(ollama_provider: OllamaProvider) -> None:
    """Test multiple consecutive generation calls.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    request1 = GenerationRequest(prompt="Test 1")
    response1 = await ollama_provider.generate(request1)
    assert isinstance(response1, GenerationResponse)
    assert len(response1.text) > 0

    request2 = GenerationRequest(prompt="Test 2")
    response2 = await ollama_provider.generate(request2)
    assert isinstance(response2, GenerationResponse)
    assert len(response2.text) > 0


@pytest.mark.asyncio
async def test_close(ollama_provider: OllamaProvider) -> None:
    """Test provider cleanup.

    Args:
        ollama_provider: OllamaProvider fixture.
    """
    await ollama_provider.close()
    # Should not raise any exception
