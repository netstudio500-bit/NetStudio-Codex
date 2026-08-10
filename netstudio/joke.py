"""Random joke generator utilities.

This module provides synchronous and asynchronous helpers to fetch a random joke
from public joke APIs and to format it for display.

It tries icanhazdadjoke.com first (returns a short one-liner), and falls back to
official-joke-api.appspot.com (returns setup + punchline) if needed.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


ICANHAZ_URL = "https://icanhazdadjoke.com/"
OFFICIAL_JOKE_URL = "https://official-joke-api.appspot.com/random_joke"


class JokeFetchError(RuntimeError):
    pass


async def fetch_joke_async(timeout: int = 10) -> Dict[str, Any]:
    """Fetch a random joke asynchronously.

    Tries icanhazdadjoke first (returns JSON with key 'joke'). If that fails,
    falls back to the official joke API (returns 'setup' and 'punchline').

    Returns a normalized dict with at least a 'text' key.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Try icanhazdadjoke
        try:
            resp = await client.get(ICANHAZ_URL, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("joke")
                if text:
                    return {"source": "icanhazdadjoke", "text": text, "raw": data}
        except httpx.HTTPError:
            # ignore and try fallback
            pass

        # Fallback to official-joke-api
        try:
            resp = await client.get(OFFICIAL_JOKE_URL, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                setup = data.get("setup")
                punchline = data.get("punchline")
                if setup or punchline:
                    text = (setup or "") + (" — " + punchline if punchline else "")
                    return {"source": "official-joke-api", "text": text, "raw": data}
        except httpx.HTTPError as exc:  # pragma: no cover - network fallback
            raise JokeFetchError("Failed to fetch joke: %s" % exc)

    raise JokeFetchError("Could not fetch a joke from known APIs")


def fetch_joke(timeout: int = 10) -> Dict[str, Any]:
    """Synchronous wrapper around fetch_joke_async."""
    with httpx.Client(timeout=timeout) as client:
        # Try icanhazdadjoke
        try:
            resp = client.get(ICANHAZ_URL, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("joke")
                if text:
                    return {"source": "icanhazdadjoke", "text": text, "raw": data}
        except httpx.HTTPError:
            pass

        # Fallback
        try:
            resp = client.get(OFFICIAL_JOKE_URL, headers={"Accept": "application/json"})
            if resp.status_code == 200:
                data = resp.json()
                setup = data.get("setup")
                punchline = data.get("punchline")
                text = (setup or "") + (" — " + punchline if punchline else "")
                return {"source": "official-joke-api", "text": text, "raw": data}
        except httpx.HTTPError as exc:  # pragma: no cover - network fallback
            raise JokeFetchError("Failed to fetch joke: %s" % exc)

    raise JokeFetchError("Could not fetch a joke from known APIs")


def format_joke(joke: Dict[str, Any]) -> str:
    """Return a user-friendly string from a joke dict produced by this module."""
    return joke.get("text", "(no joke)")
