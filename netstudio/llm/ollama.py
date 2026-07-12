"""Ollama LLM provider implementation."""

from typing import Any, Optional

import httpx

from netstudio.core.config import get_config
from netstudio.core.logger import get_logger
from netstudio.llm.base import GenerationRequest, GenerationResponse, LLMProvider

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama language model provider implementation."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None) -> None:
        """Initialize Ollama provider."""
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
        """Get provider name."""
        return "ollama"

    async def health(self) -> bool:
        """Check health of Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                is_healthy = response.status_code == 200
                logger.info(f"Ollama health check: {'OK' if is_healthy else 'FAILED'}")
                if not is_healthy:
                    raise ConnectionError(f"Ollama returned status {response.status_code}")
                return is_healthy
        except httpx.RequestError as exc:
            logger.error(f"Ollama connection error: {exc}")
            raise ConnectionError(
                f"Failed to connect to Ollama at {self._base_url}"
            ) from exc

    async def list_models(self) -> list[str]:
        """List available models in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code != 200:
                    raise ConnectionError(f"Ollama returned status {response.status_code}")
                data: dict[str, Any] = response.json()
                models = [str(model["name"]) for model in data.get("models", [])]
                logger.info(f"Found {len(models)} models in Ollama")
                return models
        except httpx.RequestError as exc:
            logger.error(f"Failed to list models: {exc}")
            raise ConnectionError(f"Failed to connect to Ollama: {exc}") from exc

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Ollama."""
        model = self._model
        logger.info(
            f"Generating with model={model}, temp={request.temperature}, "
            f"max_tokens={request.max_tokens}"
        )

        payload: dict[str, Any] = {
            "model": model,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature},
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.max_tokens is not None:
            payload["options"]["num_predict"] = request.max_tokens

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama returned status {response.status_code}")

                data: dict[str, Any] = response.json()
                generated_text = str(data.get("response", ""))
                logger.info(f"Generated {len(generated_text)} characters")

                prompt_tokens = data.get("prompt_eval_count")
                completion_tokens = data.get("eval_count")
                return GenerationResponse(
                    text=generated_text,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=(prompt_tokens or 0) + (completion_tokens or 0),
                    finish_reason="stop",
                    metadata={
                        "load_duration": data.get("load_duration"),
                        "prompt_eval_duration": data.get("prompt_eval_duration"),
                        "eval_duration": data.get("eval_duration"),
                    },
                )
        except httpx.RequestError as exc:
            logger.error(f"Generation request failed: {exc}")
            raise ConnectionError(f"Failed to connect to Ollama: {exc}") from exc
        except (KeyError, ValueError, TypeError) as exc:
            logger.error(f"Invalid response format: {exc}")
            raise RuntimeError(f"Invalid response from Ollama: {exc}") from exc

    async def close(self) -> None:
        """Close the connection and cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        logger.info("OllamaProvider closed")
