"""Definição de agente base."""

from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from netstudio.core.logger import get_logger
from netstudio.llm.base import GenerationRequest, LLMProvider
from netstudio.llm.ollama import OllamaProvider

logger = get_logger(__name__)


class Agent(BaseModel):
    """Agente mínimo funcional conectado a um provedor LLM."""

    name: str = Field(..., description="Nome do agente")
    description: str = Field(default="", description="Descrição do agente")
    system_prompt: str = Field(default="", description="Prompt do sistema")
    model: Optional[str] = Field(default=None, description="Modelo LLM a usar")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, gt=0)

    _provider: LLMProvider = PrivateAttr()
    _memories: list[str] = PrivateAttr(default_factory=list)

    def __init__(self, provider: Optional[LLMProvider] = None, **data: object) -> None:
        """Inicializa o agente com provider injetável para execução e testes."""
        super().__init__(**data)
        self._provider = provider or OllamaProvider(model=self.model)

    async def execute(self, task: str) -> str:
        """Executa uma tarefa usando o LLM configurado."""
        logger.info(f"Executing task: {task}")
        context = self._memory_context()
        prompt = (
            task if not context else f"Memória relevante:\n{context}\n\nTarefa:\n{task}"
        )
        response = await self._provider.generate(
            GenerationRequest(
                prompt=prompt,
                system_prompt=self.system_prompt or None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        )
        return response.text

    async def think(self, context: str) -> str:
        """Solicita ao LLM análise do contexto sem simular raciocínio local."""
        logger.info("Thinking about provided context")
        response = await self._provider.generate(
            GenerationRequest(
                prompt=f"Analise o contexto e proponha o próximo passo útil:\n\n{context}",
                system_prompt=self.system_prompt or None,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        )
        return response.text

    async def remember(self, memory: str) -> None:
        """Armazena memória de sessão em processo."""
        logger.info("Storing session memory")
        self._memories.append(memory)

    async def close(self) -> None:
        """Libera recursos do provider."""
        await self._provider.close()

    def _memory_context(self) -> str:
        """Monta contexto curto com as memórias da sessão."""
        return "\n".join(f"- {memory}" for memory in self._memories[-10:])
