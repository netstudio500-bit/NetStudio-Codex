"""Ponto de entrada principal da aplicação."""

import asyncio
import sys
from argparse import ArgumentParser, Namespace

from netstudio.core.agent import Agent
from netstudio.core.config import get_config
from netstudio.core.logger import get_logger

logger = get_logger(__name__)


async def _close_agent(agent: Agent, active_error: BaseException | None = None) -> None:
    try:
        await agent.close()
    except BaseException as close_error:
        if active_error is None:
            raise
        raise BaseExceptionGroup(
            "Agent operation and cleanup both failed",
            [active_error, close_error],
        ) from None


async def execute_task(agent: Agent, task: str) -> str:
    """Executa uma tarefa e garante o encerramento do provider."""
    try:
        result = await agent.execute(task)
    except BaseException as exc:
        await _close_agent(agent, exc)
        raise
    await _close_agent(agent)
    return result


async def interactive(agent: Agent) -> None:
    """Executa uma sessão interativa simples no terminal."""
    try:
        while True:
            try:
                task = input("netstudio> ").strip()
            except EOFError:
                break

            if not task:
                continue
            if task.lower() in {"exit", "quit", "sair"}:
                break

            result = await agent.execute(task)
            print(result)
            await agent.remember(f"Tarefa: {task}\nResposta: {result}")
    except BaseException as exc:
        await _close_agent(agent, exc)
        raise
    await _close_agent(agent)


async def main(args: Namespace) -> None:
    """Inicializa o agente e executa a tarefa solicitada."""
    config = get_config()
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    logger.info(f"Environment: {config.app_env}")

    if args.debug:
        config.debug = True
        config.log_level = "DEBUG"
        logger.debug("Debug mode enabled")

    agent = Agent(name="netstudio", model=args.model or config.ollama_model)

    if args.interactive or args.task is None:
        await interactive(agent)
        return

    result = await execute_task(agent, args.task)
    print(result)


def build_parser() -> ArgumentParser:
    """Cria o parser da CLI."""
    parser = ArgumentParser(description="NetStudio-Codex")
    parser.add_argument("task", nargs="?", help="Task to execute")
    parser.add_argument("-i", "--interactive", action="store_true", help="Start interactive mode")
    parser.add_argument("--model", help="Override the configured Ollama model")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--version",
        action="version",
        version="NetStudio-Codex 0.1.0",
    )
    return parser


def cli() -> None:
    """Interface de linha de comando."""
    args = build_parser().parse_args()

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
        sys.exit(0)
    except Exception as exc:
        logger.exception(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
