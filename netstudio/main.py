"""Ponto de entrada principal da aplicação."""

import asyncio
import sys
from argparse import ArgumentParser

from netstudio.core.config import get_config
from netstudio.core.logger import get_logger

logger = get_logger(__name__)


async def main(args) -> None:
    """Função main."""
    config = get_config()
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    logger.info(f"Environment: {config.app_env}")

    if args.debug:
        config.debug = True
        config.log_level = "DEBUG"
        logger.debug("Debug mode enabled")

    # TODO: Implementar inicialização completa
    logger.info("Application initialized successfully")


def cli() -> None:
    """Interface de linha de comando."""
    parser = ArgumentParser(description="NetStudio-Codex")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="NetStudio-Codex 0.1.0"
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
