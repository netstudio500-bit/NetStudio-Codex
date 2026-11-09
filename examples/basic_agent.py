"""Exemplo básico de uso de um agente."""

import asyncio

from netstudio.core.agent import Agent


async def main():
    """Main function."""
    # Criar um agente
    agent = Agent(
        name="ResearchAgent",
        description="An agent that researches topics",
        system_prompt="You are a research assistant.",
        model="llama2",
        temperature=0.7,
    )

    # Executar uma tarefa
    result = await agent.execute("What is machine learning?")
    print(f"Result: {result}")

    # Fazer o agente pensar
    thought = await agent.think("How to implement a neural network")
    print(f"Thought: {thought}")

    # Armazenar memória
    await agent.remember("Machine learning is about teaching computers to learn from data")


if __name__ == "__main__":
    asyncio.run(main())
