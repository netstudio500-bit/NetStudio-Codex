"""LLM-backed decision source and strict RuntimeDecision JSON parser."""

import json
from typing import Any

from netstudio.llm.base import GenerationRequest, LLMProvider
from netstudio.runtime.runtime import DecisionKind, Observation, RuntimeDecision
from netstudio.tools.registry import ToolRegistryView


class DecisionParseError(ValueError):
    """Raised when a provider response violates the runtime decision protocol."""


def _unwrap_json(text: str) -> str:
    """Remove only explicitly supported Markdown JSON code fences."""
    stripped = text.strip()
    if stripped.startswith("```json") and stripped.endswith("```"):
        return stripped[7:-3].strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return stripped[3:-3].strip()
    return stripped


def parse_runtime_decision(text: str) -> RuntimeDecision:
    """Parse and validate one provider response as a RuntimeDecision."""
    try:
        payload = json.loads(_unwrap_json(text))
    except json.JSONDecodeError as exc:
        raise DecisionParseError(f"Invalid decision JSON: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise DecisionParseError("Decision JSON must be an object")

    action = payload.get("action")
    if action == DecisionKind.COMPLETE.value:
        content = payload.get("content", "")
        if not isinstance(content, str):
            raise DecisionParseError("Complete decision content must be a string")
        return RuntimeDecision(DecisionKind.COMPLETE, output=content)

    if action == DecisionKind.CANCEL.value:
        content = payload.get("content", "")
        if not isinstance(content, str):
            raise DecisionParseError("Cancel decision content must be a string")
        return RuntimeDecision(DecisionKind.CANCEL, output=content)

    if action == DecisionKind.TOOL.value:
        tool_name = payload.get("tool_name")
        arguments = payload.get("arguments", {})
        if not isinstance(tool_name, str) or not tool_name.strip():
            raise DecisionParseError("Tool decision requires a non-empty tool_name")
        if not isinstance(arguments, dict):
            raise DecisionParseError("Tool decision arguments must be a JSON object")
        return RuntimeDecision(
            DecisionKind.TOOL,
            tool_name=tool_name,
            arguments=arguments,
        )

    raise DecisionParseError(f"Unknown decision action: {action!r}")


class LLMDecisionSource:
    """Adapt an LLMProvider to the runtime's existing DecisionSource contract."""

    def __init__(
        self,
        provider: LLMProvider,
        tools: ToolRegistryView,
        system_prompt: str = "",
        memory_context: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._system_prompt = system_prompt
        self._memory_context = memory_context
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def decide(
        self, task: str, observations: tuple[Observation, ...], iteration: int
    ) -> RuntimeDecision:
        """Ask the provider for one structured decision and validate it."""
        response = await self._provider.generate(
            GenerationRequest(
                prompt=self._build_prompt(task, observations, iteration),
                system_prompt=self._system_prompt or None,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        )
        return parse_runtime_decision(response.text)

    def _build_prompt(
        self, task: str, observations: tuple[Observation, ...], iteration: int
    ) -> str:
        tools = [self._tool_contract(name) for name in self._tools.names()]
        observation_data = [
            {
                "tool_name": observation.tool_name,
                "success": observation.result.success,
                "output": observation.result.output,
                "error": observation.result.error,
                "metadata": observation.result.metadata,
            }
            for observation in observations
        ]
        return (
            "You are the decision source for AgentRuntime. Return exactly one JSON object "
            "and no prose. Allowed actions are complete, tool, and cancel. "
            'Complete format: {"action":"complete","content":"result"}. '
            'Tool format: {"action":"tool","tool_name":"name","arguments":{}}. '
            'Cancel format: {"action":"cancel","content":"reason"}. '
            "Use only tools listed in available_tools. If no tool is needed, complete the task.\n\n"
            f"task={json.dumps(task, ensure_ascii=False)}\n"
            f"memory_context={json.dumps(self._memory_context, ensure_ascii=False)}\n"
            f"iteration={iteration}\n"
            f"available_tools={json.dumps(tools, ensure_ascii=False)}\n"
            f"observations={json.dumps(observation_data, ensure_ascii=False)}"
        )

    def _tool_contract(self, name: str) -> dict[str, Any]:
        metadata = self._tools.get(name).metadata
        return {
            "name": metadata.name,
            "description": metadata.description,
            "argument_schema": metadata.argument_schema,
        }
