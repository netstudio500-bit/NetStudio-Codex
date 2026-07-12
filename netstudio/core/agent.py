"""Definição de agente base."""

from typing import Optional

from pydantic import BaseModel, Field

from netstudio.core.logger import get_logger

logger = get_logger(__name__)


class Agent(BaseModel):
    """Definição base de um agente."""

    name: str = Field(..., description="Nome do agente")
    description: str = Field(default="", description="Descrição do agente")
    system_prompt: str = Field(default="", description="Prompt do sistema")
    model: Optional[str] = Field(default=None, description="Modelo LLM a usar")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, gt=0)

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True

    async def execute(self, task: str) -> str:
        """Executar uma tarefa.

        Args:
            task: Tarefa a executar

        Returns:
            Resultado da execução
        """
        logger.info(f"Executing task: {task}")
        # TODO: Implementar execução real
        return f"Executed: {task}"

    async def think(self, context: str) -> str:
        """Pensar sobre um contexto.

        Args:
            context: Contexto para pensar

        Returns:
            Resultado do pensamento
        """
        logger.info(f"Thinking about: {context}")
        # TODO: Implementar raciocínio real
        return f"Thought about: {context}"

    async def remember(self, memory: str) -> None:
        """Armazenar memória.

        Args:
            memory: Memória a armazenar
        """
        logger.info(f"Storing memory: {memory}")
        # TODO: Implementar armazenamento real
