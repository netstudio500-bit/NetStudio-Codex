"""Ollama LLM provider implementation."""

from typing import Optional

import httpx

from netstudio.core.config import get_config
from netstudio.core.logger import get_logger
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama language model provider implementation.

    Provides integration with Ollama for running local language models.
    Supports health checks, model listing, and text generation.
    """

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama server base URL. If not provided, uses config.
            model: Default model name. If not provided, uses config.

        Example:
            provider = OllamaProvider()
            provider = OllamaProvider("http://localhost:11434", "llama2")
        """
        config = get_config()
        self._base_url = base_url or config.ollama_base_url
        self._model = model or config.ollama_model
        self._timeout = 30.0
        self._client: Optional[httpx.AsyncClient] = None
        logger.info(
            f"Initialized OllamaProvider: base_url={self._base_url}, model={self._model}"
        )

    @property
    def name(self) -> str:
        """Get provider name.

        Returns:
            str: Provider identifier.
        """
        return "ollama"

    async def health(self) -> bool:
        """Check health of Ollama server.

        Attempts to connect to the Ollama API tags endpoint
        to verify the server is running and responding.

        Returns:
            bool: True if Ollama is healthy and reachable.

        Raises:
            ConnectionError: If Ollama cannot be reached.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                is_healthy = response.status_code == 200
                logger.info(f"Ollama health check: {'OK' if is_healthy else 'FAILED'}")
                if not is_healthy:
                    raise ConnectionError(
                        f"Ollama returned status {response.status_code}"
                    )
                return is_healthy
        except httpx.RequestError as e:
            logger.error(f"Ollama connection error: {e}")
            raise ConnectionError(f"Failed to connect to Ollama at {self._base_url}") from e

    async def list_models(self) -> list[str]:
        """List available models in Ollama.

        Fetches the list of all models currently available
        in the Ollama server.

        Returns:
            list[str]: List of model identifiers.

        Raises:
            ConnectionError: If Ollama cannot be reached.
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(
                        f"Ollama returned status {response.status_code}"
                    )
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                logger.info(f"Found {len(models)} models in Ollama")
                return models
        except httpx.RequestError as e:
            logger.error(f"Failed to list models: {e}")
            raise ConnectionError(f"Failed to connect to Ollama: {e}") from e

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Ollama.

        Uses the specified model to generate text based on the provided prompt
        and parameters.

        Args:
            request: Generation request with prompt and parameters.

        Returns:
            GenerationResponse: Generated text and metadata.

        Raises:
            ConnectionError: If Ollama cannot be reached.
            ValueError: If request parameters are invalid.
            RuntimeError: If generation fails.

        Example:
            request = GenerationRequest(prompt="Hello world")
            response = await provider.generate(request)
            print(response.text)
        """
        model = self._model
        logger.info(
            f"Generating with model={model}, "
            f"temp={request.temperature}, "
            f"max_tokens={request.max_tokens}"
        )

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                payload = {
                    "model": model,
                    "prompt": request.prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                    },
                }

                if request.system_prompt:
                    payload["system"] = request.system_prompt

                if request.max_tokens:
                    payload["options"]["num_predict"] = request.max_tokens

                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Ollama returned status {response.status_code}"
                    )

                data = response.json()
                generated_text = data.get("response", "")

                logger.info(f"Generated {len(generated_text)} characters")

                return GenerationResponse(
                    text=generated_text,
                    model=model,
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                    total_tokens=(
                        (data.get("prompt_eval_count") or 0)
                        + (data.get("eval_count") or 0)
                    ),
                    finish_reason="stop",
                    metadata={
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_duration": data.get("prompt_eval_duration"),
                        "eval_duration": data.get("eval_duration"),
                    },
                )

        except httpx.RequestError as e:
            logger.error(f"Generation request failed: {e}")
            raise ConnectionError(f"Failed to connect to Ollama: {e}") from e
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid response format: {e}")
            raise RuntimeError(f"Invalid response from Ollama: {e}") from e

    async def close(self) -> None:
        """Close the connection and cleanup resources.

        This method should be called when the provider is no longer needed.
        Currently, httpx clients are created per request, so this is a no-op,
        but the method is implemented for consistency with the interface.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("OllamaProvider closed")
