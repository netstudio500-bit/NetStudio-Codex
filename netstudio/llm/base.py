"""Base abstractions for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GenerationRequest:
    """Request object for text generation.

    Attributes:
        prompt: The main prompt/input text for generation.
        system_prompt: Optional system prompt to set the context/behavior.
        temperature: Sampling temperature (0.0-1.0). Higher = more random.
        max_tokens: Maximum tokens to generate. None = use provider default.
    """

    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None


@dataclass
class GenerationResponse:
    """Response object for text generation.

    Attributes:
        text: The generated text.
        model: Name of the model used for generation.
        prompt_tokens: Number of tokens in the prompt.
        completion_tokens: Number of tokens generated.
        total_tokens: Total tokens used (prompt + completion).
        finish_reason: Reason generation stopped (e.g., "stop", "length").
        metadata: Additional provider-specific metadata.
    """

    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for Language Model providers.

    All LLM provider implementations must inherit from this class
    and implement all abstract methods. This ensures a consistent
    interface across different LLM services.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the name/identifier of this provider.

        Returns:
            str: Provider name (e.g., "ollama", "openai", "anthropic").
        """

    @abstractmethod
    async def health(self) -> bool:
        """Check the health of the provider.

        Returns:
            bool: True if the provider is available and healthy.

        Raises:
            ConnectionError: If the provider cannot be reached.
        """

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List all available models from this provider.

        Returns:
            list[str]: List of available model identifiers.

        Raises:
            ConnectionError: If the provider cannot be reached.
        """

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text based on the given request.

        Args:
            request: The generation request containing prompt and parameters.

        Returns:
            GenerationResponse: The generated text and metadata.

        Raises:
            ConnectionError: If the provider cannot be reached.
            ValueError: If the request parameters are invalid.
            RuntimeError: If generation fails for any other reason.
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the connection and cleanup resources.

        This method should be called when the provider is no longer needed.
        It allows for graceful shutdown and resource cleanup.
        """
