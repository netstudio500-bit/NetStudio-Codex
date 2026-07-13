"""Definição de agente base."""

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from netstudio.core.logger import get_logger
from netstudio.llm.base import GenerationRequest, LLMProvider
from netstudio.llm.ollama import OllamaProvider
from netstudio.runtime import (
    AgentRuntime,
    ExecutionContext,
    LLMDecisionSource,
    PolicySnapshot,
    RuntimeFailure,
    RuntimeState,
    ScopeRef,
)
from netstudio.tools import ShellTool, ToolRegistry

logger = get_logger(__name__)


class AgentRuntimeError(RuntimeError):
    """Public agent error preserving the structured runtime failure."""

    def __init__(self, failure: RuntimeFailure) -> None:
        super().__init__(f"{failure.code}: {failure.message}")
        self.failure = failure


class Agent(BaseModel):
    """Agente operacional cuja execução padrão atravessa AgentRuntime."""

    name: str = Field(..., description="Nome do agente")
    description: str = Field(default="", description="Descrição do agente")
    system_prompt: str = Field(default="", description="Prompt do sistema")
    model: Optional[str] = Field(default=None, description="Modelo LLM a usar")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=2048, gt=0)
    max_iterations: int = Field(default=8, gt=0)

    _provider: LLMProvider = PrivateAttr()
    _registry: ToolRegistry = PrivateAttr()
    _policy: PolicySnapshot = PrivateAttr()
    _workspace_root: Path = PrivateAttr()
    _memories: list[str] = PrivateAttr(default_factory=list)

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        registry: Optional[ToolRegistry] = None,
        policy: Optional[PolicySnapshot] = None,
        workspace_root: Optional[Path] = None,
        **data: object,
    ) -> None:
        """Inicializa o agente com dependências e autorização explicitamente injetáveis."""
        super().__init__(**data)
        self._provider = provider or OllamaProvider(model=self.model)
        self._workspace_root = (workspace_root or Path.cwd()).resolve(strict=True)
        self._policy = policy or PolicySnapshot()
        if registry is None:
            registry = ToolRegistry()
            registry.register(ShellTool(self._workspace_root))
        self._registry = registry

    async def execute(self, task: str) -> str:
        """Executa uma tarefa pelo AgentRuntime e retorna seu resultado público."""
        logger.info("Executing task through AgentRuntime")
        execution_context = self._execution_context()
        decision_source = LLMDecisionSource(
            provider=self._provider,
            tools=self._registry.view(execution_context),
            system_prompt=self.system_prompt,
            memory_context=self._memory_context(),
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        result = await AgentRuntime(
            decision_source=decision_source,
            registry=self._registry,
            context=execution_context,
            max_iterations=self.max_iterations,
        ).run(task)
        if result.failure is not None:
            raise AgentRuntimeError(result.failure)
        if result.state is RuntimeState.CANCELLED:
            return result.output
        return result.output

    async def think(self, context: str) -> str:
        """Solicita ao LLM análise do contexto fora do fluxo operacional de tarefa."""
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

    def _execution_context(self) -> ExecutionContext:
        """Resolve o workspace e a policy desta execução."""
        return ExecutionContext(
            scope=ScopeRef(
                scope_id=self.name,
                scope_type="agent",
                workspace_root=self._workspace_root,
            ),
            policy=self._policy,
        )

    def _memory_context(self) -> str:
        """Monta contexto curto com as memórias da sessão."""
        return "\n".join(f"- {memory}" for memory in self._memories[-10:])
