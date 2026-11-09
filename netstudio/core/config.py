"""Gerenciamento centralizado de configuração."""

from functools import lru_cache
from typing import Any, Optional

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Configuração centralizada da aplicação."""

    # App
    app_name: str = "NetStudio-Codex"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    ollama_embedding_model: str = "nomic-embed-text"

    # Database
    database_url: str = "sqlite:///./netstudio.db"

    # Vector Store
    vector_store_type: str = "chroma"
    vector_store_path: str = "./data/vector_store"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4

    # WebSocket
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8001

    # Memory
    max_memory_size: int = 1000
    memory_retention_days: int = 90

    # Workspace
    workspace_root: str = "./workspaces"
    max_workspace_size: str = "10GB"

    # Plugins
    plugin_directory: str = "./plugins"
    auto_load_plugins: bool = True

    # Recovery
    checkpoint_interval: int = 300
    max_checkpoints: int = 10

    # Tools
    tools_timeout: int = 30
    max_tool_workers: int = 4

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Get configuration value."""
        return getattr(self, key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        setattr(self, key, value)


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get global config instance."""
    return Config()
