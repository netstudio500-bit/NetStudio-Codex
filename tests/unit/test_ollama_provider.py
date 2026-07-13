"""Unit tests for malformed Ollama responses."""

from typing import Any

import pytest

from netstudio.llm.base import GenerationRequest
from netstudio.llm.ollama import OllamaProvider


class StubResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        if isinstance(self.payload, ValueError):
            raise self.payload
        return self.payload


class StubAsyncClient:
    response = StubResponse({})

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout

    async def __aenter__(self) -> "StubAsyncClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object,
    ) -> None:
        return None

    async def get(self, url: str) -> StubResponse:
        return self.response

    async def post(self, url: str, json: dict[str, Any]) -> StubResponse:
        return self.response


@pytest.mark.asyncio
async def test_list_models_rejects_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    StubAsyncClient.response = StubResponse(ValueError("invalid json"))
    monkeypatch.setattr("netstudio.llm.ollama.httpx.AsyncClient", StubAsyncClient)

    with pytest.raises(RuntimeError, match="invalid JSON") as error:
        await OllamaProvider().list_models()

    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.asyncio
async def test_list_models_rejects_malformed_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    StubAsyncClient.response = StubResponse({"models": [{"name": None}]})
    monkeypatch.setattr("netstudio.llm.ollama.httpx.AsyncClient", StubAsyncClient)

    with pytest.raises(RuntimeError, match="non-empty name"):
        await OllamaProvider().list_models()


@pytest.mark.asyncio
async def test_generate_rejects_missing_response_text(monkeypatch: pytest.MonkeyPatch) -> None:
    StubAsyncClient.response = StubResponse({"eval_count": 1})
    monkeypatch.setattr("netstudio.llm.ollama.httpx.AsyncClient", StubAsyncClient)

    with pytest.raises(RuntimeError, match="response text"):
        await OllamaProvider().generate(GenerationRequest(prompt="test"))
