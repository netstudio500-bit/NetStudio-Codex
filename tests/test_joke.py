import pytest

from types import SimpleNamespace

import asyncio

from netstudio import joke


class DummyResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


class DummyAResponse(DummyResponse):
    def json(self):
        return self._data


@pytest.mark.asyncio
async def test_fetch_joke_async_icanhaz(monkeypatch):
    async def fake_get(url, headers=None):
        if "icanhazdadjoke" in url:
            return DummyAResponse(200, {"joke": "I would tell you a UDP joke, but you might not get it."})
        return DummyAResponse(404, {})

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            return await fake_get(url, headers=headers)

    monkeypatch.setattr(joke, "httpx", SimpleNamespace(AsyncClient=lambda timeout=None: DummyClient()))

    result = await joke.fetch_joke_async()
    assert "I would tell you a UDP joke" in result["text"]
    assert result["source"] == "icanhazdadjoke"


def test_fetch_joke_sync_official(monkeypatch):
    def fake_get(url, headers=None):
        if "official-joke-api" in url:
            return DummyResponse(200, {"setup": "Why did the programmer quit his job?", "punchline": "Because he didn't get arrays."})
        return DummyResponse(404, {})

    class DummyClient:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, url, headers=None):
            return fake_get(url, headers=headers)

    monkeypatch.setattr(joke, "httpx", SimpleNamespace(Client=lambda timeout=None: DummyClient()))

    result = joke.fetch_joke()
    assert "Why did the programmer quit his job" in result["text"]
    assert result["source"] == "official-joke-api"
