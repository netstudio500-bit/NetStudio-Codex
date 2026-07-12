"""FastAPI application for NetStudio-Codex."""

from fastapi import FastAPI

from netstudio import __version__

app = FastAPI(
    title="NetStudio-Codex",
    description="Um Codex local, gratuito e modular para agentes de IA",
    version=__version__,
    docs_url="/docs",
    openapi_url="/openapi.json",
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
