"""Ponto de entrada principal da aplicação."""

import asyncio
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path

from netstudio.core.agent import Agent
from netstudio.core.config import get_config
from netstudio.core.logger import get_logger
from netstudio.runtime import PolicySnapshot, ToolCapability

logger = get_logger(__name__)


def build_policy(args: Namespace) -> PolicySnapshot:
    """Constrói a policy imutável exclusivamente a partir de concessões da CLI."""
    capabilities: set[ToolCapability] = set()
    if args.allow_local_execution:
        capabilities.add(ToolCapability.LOCAL_EXECUTION)
    return PolicySnapshot(frozenset(capabilities))


async def execute_task(agent: Agent, task: str) -> str:
    """Executa uma tarefa e garante o encerramento do provider."""
    try:
        return await agent.execute(task)
    finally:
        await agent.close()


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
    finally:
        await agent.close()


async def main(args: Namespace) -> None:
    """Inicializa o agente e executa a tarefa solicitada."""
    config = get_config()
    logger.info(f"Starting {config.app_name} v{config.app_version}")
    logger.info(f"Environment: {config.app_env}")

    if args.debug:
        config.debug = True
        config.log_level = "DEBUG"
        logger.debug("Debug mode enabled")

    policy = build_policy(args)
    workspace_root = Path.cwd().resolve(strict=True)
    agent = Agent(
        name="netstudio",
        model=args.model or config.ollama_model,
        policy=policy,
        workspace_root=workspace_root,
    )

    if args.allow_local_execution:
        print("Local process execution authorized for this workspace.")

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
        "--allow-local-execution",
        action="store_true",
        help="Allow the agent to execute local processes inside the authorized workspace",
    )
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
        logger.error(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
