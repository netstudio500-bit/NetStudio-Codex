"""FastAPI application for NetStudio-Codex."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from netstudio import __version__
from netstudio.core.config import get_config

config = get_config()

app = FastAPI(
    title="NetStudio-Codex",
    description="Um Codex local, gratuito e modular para agentes de IA",
    version=__version__,
    docs_url="/docs" if config.debug else None,
    openapi_url="/openapi.json" if config.debug else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip() for origin in config.allowed_origins.split(",") if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/", tags=["Info"])
async def root() -> dict[str, str]:
    """Return API information."""
    return {
        "name": "NetStudio-Codex",
        "version": __version__,
        "status": "ok",
    }


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "healthy"}
