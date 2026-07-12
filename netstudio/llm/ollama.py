"""Ollama LLM provider implementation."""

from typing import Any, Dict, List, Optional

import httpx

from netstudio.core.config import get_config
from netstudio.core.logger import get_logger
from netstudio.llm.base import LLMProvider

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        """Initialize Ollama provider.

        Args:
            base_url: Ollama base URL (defaults to config)
            model: Model name (defaults to config)
        """
        config = get_config()
        self.base_url = base_url or config.ollama_base_url
        self.model = model or config.ollama_model
        self.timeout = 30.0
        logger.info(f"Initialized OllamaProvider: {self.base_url}, model={self.model}")

    async def health(self) -> Dict[str, Any]:
        """Check health of Ollama server.

        Returns:
            dict: Health status

        Raises:
            RuntimeError: If connection fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    logger.info("Ollama health check: OK")
                    return {
                        "status": "healthy",
                        "provider": "ollama",
                        "base_url": self.base_url,
                        "model": self.model,
                    }
                else:
                    logger.error(f"Ollama health check failed: {response.status_code}")
                    raise RuntimeError(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
            raise RuntimeError(f"Failed to connect to Ollama: {e}")

    async def list_models(self) -> List[str]:
        """List available models in Ollama.

        Returns:
            List[str]: List of model names

        Raises:
            RuntimeError: If request fails
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    logger.info(f"Found {len(models)} models: {models}")
                    return models
                else:
                    logger.error(f"Failed to list models: {response.status_code}")
                    raise RuntimeError(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise RuntimeError(f"Failed to list models: {e}")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text using Ollama.

        Args:
            prompt: Input prompt
            model: Model name (uses default if not specified)
            temperature: Sampling temperature
            max_tokens: Maximum tokens

        Returns:
            str: Generated text

        Raises:
            RuntimeError: If generation fails
        """
        model_name = model or self.model
        logger.info(f"Generating with model={model_name}, temp={temperature}")

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    generated_text = data.get("response", "")
                    logger.info(f"Generated {len(generated_text)} characters")
                    return generated_text
                else:
                    logger.error(f"Generation failed: {response.status_code}")
                    raise RuntimeError(f"Ollama returned status {response.status_code}")
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise RuntimeError(f"Failed to generate text: {e}")

    def model_name(self) -> str:
        """Get the default model name.

        Returns:
            str: Model name
        """
        return self.model
