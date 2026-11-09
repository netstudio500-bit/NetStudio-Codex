"""Logging centralizado."""

import sys
from typing import Any, Optional

from loguru import logger as loguru_logger

from netstudio.core.config import get_config


class Logger:
    """Logger wrapper."""

    def __init__(self, name: Optional[str] = None) -> None:
        """Initialize logger."""
        self.logger = loguru_logger.bind(name=name or "netstudio")
        config = get_config()
        self.logger.remove()
        self.logger.add(
            sys.stdout,
            level=config.log_level,
            format=(
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
        )

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self.logger.critical(message, **kwargs)


def get_logger(name: Optional[str] = None) -> Logger:
    """Get logger instance."""
    return Logger(name)
