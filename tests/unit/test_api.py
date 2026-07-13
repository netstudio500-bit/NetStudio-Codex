"""Security-focused tests for the FastAPI application."""

from fastapi.middleware.cors import CORSMiddleware

from netstudio.api import app


def test_api_docs_are_disabled_by_default() -> None:
    assert app.docs_url is None
    assert app.openapi_url is None


def test_api_uses_cors_middleware() -> None:
    assert any(middleware.cls is CORSMiddleware for middleware in app.user_middleware)
