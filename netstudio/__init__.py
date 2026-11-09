"""NetStudio-Codex: Um Codex local, gratuito e modular para agentes de IA."""

__version__ = "0.1.0"
__author__ = "NetStudio"
__license__ = "MIT"

from netstudio.core.agent import Agent
from netstudio.core.config import Config
from netstudio.core.logger import get_logger

__all__ = ["Agent", "Config", "get_logger"]
