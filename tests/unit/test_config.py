"""Tests for configuration."""

from netstudio.core.config import Config


class TestConfig:
    """Config tests."""

    def test_config_initialization(self) -> None:
        """Test config initialization."""
        config = Config()
        assert config.app_name == "NetStudio-Codex"
        assert config.app_version == "0.1.0"

    def test_config_get(self) -> None:
        """Test config get method."""
        config = Config()
        assert config.get("app_name") == "NetStudio-Codex"
        assert config.get("nonexistent", "default") == "default"

    def test_config_set(self) -> None:
        """Test config set method."""
        config = Config()
        config.set("app_env", "production")
        assert config.app_env == "production"
