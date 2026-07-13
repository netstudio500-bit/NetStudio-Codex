"""Behavior tests for policy snapshots and the ToolRegistry."""

from typing import Any

import pytest

from netstudio.runtime import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.tools import (
    DuplicateToolError,
    Tool,
    ToolCapability,
    ToolMetadata,
    ToolNotFoundError,
    ToolRegistry,
    ToolResult,
)


class CapabilityTool(Tool):
    """Concrete tool with configurable capabilities for registry tests."""

    def __init__(self, name: str, *capabilities: ToolCapability) -> None:
        self._metadata = ToolMetadata(name, "test tool", frozenset(capabilities))

    @property
    def metadata(self) -> ToolMetadata:
        return self._metadata

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(success=True, output="executed")


def context(*capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        ScopeRef("scope"), PolicySnapshot(frozenset(capabilities))
    )


def test_registry_registers_and_finds_tool() -> None:
    tool = CapabilityTool("reader", ToolCapability.READ)
    registry = ToolRegistry()

    registry.register(tool)

    assert registry.get("reader") is tool


def test_registry_rejects_duplicate_tool_name() -> None:
    registry = ToolRegistry()
    registry.register(CapabilityTool("reader", ToolCapability.READ))

    with pytest.raises(DuplicateToolError, match="reader"):
        registry.register(CapabilityTool("reader", ToolCapability.WRITE))


def test_registry_reports_missing_tool() -> None:
    registry = ToolRegistry()

    with pytest.raises(ToolNotFoundError, match="missing"):
        registry.get("missing")


def test_policy_allows_explicitly_granted_capability() -> None:
    policy = PolicySnapshot(frozenset({ToolCapability.READ}))

    assert policy.permits(frozenset({ToolCapability.READ})) is True


def test_policy_denies_capability_not_granted() -> None:
    policy = PolicySnapshot(frozenset({ToolCapability.READ}))

    assert policy.permits(frozenset({ToolCapability.WRITE})) is False


def test_policy_is_deny_by_default() -> None:
    policy = PolicySnapshot()

    assert policy.permits(frozenset({ToolCapability.READ})) is False


def test_policy_always_blocks_unclassified_capability() -> None:
    policy = PolicySnapshot(frozenset({ToolCapability.UNCLASSIFIED}))

    assert policy.permits(frozenset({ToolCapability.UNCLASSIFIED})) is False


def test_registry_view_contains_only_policy_permitted_tools() -> None:
    registry = ToolRegistry()
    registry.register(CapabilityTool("reader", ToolCapability.READ))
    registry.register(CapabilityTool("writer", ToolCapability.WRITE))

    view = registry.view(context(ToolCapability.READ))

    assert view.names() == ("reader",)
    assert view.get("reader").metadata.name == "reader"
    with pytest.raises(ToolNotFoundError, match="writer"):
        view.get("writer")


def test_registry_view_excludes_unclassified_tool() -> None:
    registry = ToolRegistry()
    registry.register(CapabilityTool("unknown", ToolCapability.UNCLASSIFIED))

    view = registry.view(context(ToolCapability.UNCLASSIFIED))

    assert view.names() == ()
