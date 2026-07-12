"""Tests for LLM base classes and interfaces."""

import pytest

from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider


class TestGenerationRequest:
    """Tests for GenerationRequest dataclass."""

    def test_generation_request_basic(self) -> None:
        """Test basic GenerationRequest instantiation."""
        request = GenerationRequest(prompt="Hello, world!")
        assert request.prompt == "Hello, world!"
        assert request.system_prompt is None
        assert request.temperature == 0.7
        assert request.max_tokens is None

    def test_generation_request_with_all_fields(self) -> None:
        """Test GenerationRequest with all fields specified."""
        request = GenerationRequest(
            prompt="Test prompt",
            system_prompt="You are helpful",
            temperature=0.5,
            max_tokens=100,
        )
        assert request.prompt == "Test prompt"
        assert request.system_prompt == "You are helpful"
        assert request.temperature == 0.5
        assert request.max_tokens == 100

    def test_generation_request_temperature_bounds(self) -> None:
        """Test GenerationRequest temperature values."""
        request_cold = GenerationRequest(prompt="test", temperature=0.0)
        assert request_cold.temperature == 0.0

        request_hot = GenerationRequest(prompt="test", temperature=1.0)
        assert request_hot.temperature == 1.0


class TestGenerationResponse:
    """Tests for GenerationResponse dataclass."""

    def test_generation_response_basic(self) -> None:
        """Test basic GenerationResponse instantiation."""
        response = GenerationResponse(text="Generated text", model="llama2")
        assert response.text == "Generated text"
        assert response.model == "llama2"
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None
        assert response.finish_reason is None
        assert response.metadata == {}

    def test_generation_response_with_all_fields(self) -> None:
        """Test GenerationResponse with all fields specified."""
        metadata = {"duration": 1.5}
        response = GenerationResponse(
            text="Generated",
            model="llama2",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            finish_reason="stop",
            metadata=metadata,
        )
        assert response.text == "Generated"
        assert response.model == "llama2"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == "stop"
        assert response.metadata == metadata

    def test_generation_response_metadata_default(self) -> None:
        """Test that metadata defaults to empty dict."""
        response1 = GenerationResponse(text="test", model="llama2")
        response2 = GenerationResponse(text="test", model="llama2")
        assert response1.metadata == {}
        assert response2.metadata == {}
        # Ensure they are different instances
        assert response1.metadata is not response2.metadata


class TestLLMProviderAbstraction:
    """Tests for LLMProvider abstract base class."""

    def test_llm_provider_is_abstract(self) -> None:
        """Test that LLMProvider cannot be instantiated."""
        with pytest.raises(TypeError):
            LLMProvider()  # type: ignore

    def test_llm_provider_requires_implementation(self) -> None:
        """Test that implementing LLMProvider requires all abstract methods."""

        class IncompleteProvider(LLMProvider):
            """Incomplete provider missing required methods."""

            @property
            def name(self) -> str:
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteProvider()  # type: ignore

    def test_llm_provider_complete_implementation(self) -> None:
        """Test that a complete implementation can be instantiated."""

        class CompleteProvider(LLMProvider):
            """Complete provider implementation."""

            @property
            def name(self) -> str:
                return "complete"

            async def health(self) -> bool:
                return True

            async def list_models(self) -> list[str]:
                return ["model1", "model2"]

            async def generate(
                self, request: GenerationRequest
            ) -> GenerationResponse:
                return GenerationResponse(text="response", model="model1")

            async def close(self) -> None:
                pass

        provider = CompleteProvider()
        assert provider.name == "complete"
