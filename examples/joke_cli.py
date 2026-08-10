#!/usr/bin/env python3
"""Example CLI to print a random joke using netstudio.joke.

Usage: python examples/joke_cli.py
"""
import asyncio

from netstudio.joke import fetch_joke_async, format_joke


async def main() -> None:
    try:
        joke = await fetch_joke_async()
        print("\nHere's a joke for you:\n")
        print(format_joke(joke))
    except Exception as exc:
        print("Failed to fetch a joke:", exc)


if __name__ == "__main__":
    asyncio.run(main())
