"""Behavioral and security tests for WriteFileTool."""

import json
import os
from pathlib import Path

import pytest

from netstudio.runtime import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools import (
    ListFilesTool,
    ReadFileTool,
    SearchTextTool,
    ShellTool,
    ToolRegistry,
    WriteFileTool,
)
from netstudio.tools.write_file import DEFAULT_MAX_WRITE_SIZE_BYTES


def failure(result, code: str) -> None:
    assert result.success is False
    assert result.metadata["code"] == code


def payload(result):
    return json.loads(result.output)


def test_metadata_and_schema(tmp_path: Path) -> None:
    metadata = WriteFileTool(tmp_path).metadata
    assert metadata.name == "write_file"
    assert metadata.capabilities == frozenset({ToolCapability.WRITE})
    assert metadata.argument_schema["properties"]["create"]["default"] is False
    assert metadata.argument_schema["properties"]["overwrite"]["default"] is False
    assert metadata.argument_schema["additionalProperties"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"path": 1, "content": "x"},
        {"path": "", "content": "x"},
        {"path": "x"},
        {"path": "x", "content": 1},
        {"path": "x", "content": "x", "create": 1},
        {"path": "x", "content": "x", "overwrite": 0},
        {"path": "x", "content": "x", "extra": True},
    ],
)
async def test_invalid_arguments(tmp_path: Path, arguments: dict[str, object]) -> None:
    failure(await WriteFileTool(tmp_path).execute(arguments), "invalid_arguments")


@pytest.mark.asyncio
async def test_create_and_explicit_intent_rules(tmp_path: Path) -> None:
    tool = WriteFileTool(tmp_path)
    failure(await tool.execute({"path": "new.txt", "content": "x"}), "create_not_allowed")
    created = await tool.execute({"path": "new.txt", "content": "olá", "create": True})
    assert created.success and (tmp_path / "new.txt").read_bytes() == "olá".encode()
    assert payload(created)["operation"] == "created"
    assert payload(created)["checkpoint_created"] is False
    failure(
        await tool.execute({"path": "new.txt", "content": "bad", "create": True}),
        "overwrite_not_allowed",
    )
    assert (tmp_path / "new.txt").read_text(encoding="utf-8") == "olá"


@pytest.mark.asyncio
async def test_overwrite_creates_exact_unique_checkpoints_and_diff(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_bytes(b"OLD_VALUE")
    tool = WriteFileTool(tmp_path)
    first = await tool.execute({"path": "target.txt", "content": "NEW_VALUE", "overwrite": True})
    first_data = payload(first)
    checkpoint = tmp_path / ".netstudio" / "checkpoints" / f"{first_data['checkpoint_id']}.bin"
    assert checkpoint.read_bytes() == b"OLD_VALUE"
    assert first_data["checkpoint_created"] is True
    assert "-OLD_VALUE" in first_data["diff"] and "+NEW_VALUE" in first_data["diff"]
    assert "a/target.txt" in first_data["diff"]
    second = await tool.execute({"path": "target.txt", "content": "FINAL", "overwrite": True})
    assert payload(second)["checkpoint_id"] != first_data["checkpoint_id"]
    assert target.read_text(encoding="utf-8") == "FINAL"


@pytest.mark.asyncio
async def test_byte_limit_uses_utf8_bytes(tmp_path: Path) -> None:
    tool = WriteFileTool(tmp_path, max_write_size_bytes=3)
    failure(
        await tool.execute({"path": "x.txt", "content": "éé", "create": True}), "content_too_large"
    )
    assert not (tmp_path / "x.txt").exists()
    assert DEFAULT_MAX_WRITE_SIZE_BYTES == 1024 * 1024


@pytest.mark.asyncio
async def test_path_parent_directory_and_reserved_area_controls(tmp_path: Path) -> None:
    external = tmp_path.parent / "external-write.txt"
    tool = WriteFileTool(tmp_path)
    failure(
        await tool.execute({"path": "../external-write.txt", "content": "x", "create": True}),
        "path_outside_workspace",
    )
    failure(
        await tool.execute({"path": str(external.resolve()), "content": "x", "create": True}),
        "path_outside_workspace",
    )
    failure(
        await tool.execute({"path": "missing/x.txt", "content": "x", "create": True}),
        "parent_not_found",
    )
    (tmp_path / "folder").mkdir()
    failure(await tool.execute({"path": "folder", "content": "x", "overwrite": True}), "not_a_file")
    failure(
        await tool.execute({"path": ".netstudio/user.txt", "content": "x", "create": True}),
        "reserved_internal_path",
    )


@pytest.mark.asyncio
async def test_external_symlink_is_not_writable(tmp_path: Path) -> None:
    external = tmp_path.parent / "external-target.txt"
    external.write_text("SECRET", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(external)
    except OSError as exc:
        if os.name == "nt":
            pytest.skip(f"Windows host denied symlink creation: {exc}")
        raise
    result = await WriteFileTool(tmp_path).execute(
        {"path": "link.txt", "content": "BAD", "overwrite": True}
    )
    failure(result, "path_outside_workspace")
    assert external.read_text(encoding="utf-8") == "SECRET"


@pytest.mark.asyncio
async def test_atomic_replace_failure_preserves_original_and_cleans_temp(
    tmp_path: Path, monkeypatch
) -> None:
    target = tmp_path / "target.txt"
    target.write_text("ORIGINAL", encoding="utf-8")
    monkeypatch.setattr(
        "netstudio.tools.write_file.os.replace",
        lambda *_: (_ for _ in ()).throw(OSError("replace failed")),
    )
    result = await WriteFileTool(tmp_path).execute(
        {"path": "target.txt", "content": "NEW", "overwrite": True}
    )
    failure(result, "write_failed")
    assert target.read_text(encoding="utf-8") == "ORIGINAL"
    assert list(tmp_path.glob(".netstudio-write-*")) == []


@pytest.mark.asyncio
async def test_diff_truncation_does_not_revert_write(tmp_path: Path) -> None:
    result = await WriteFileTool(tmp_path, max_diff_chars=10).execute(
        {"path": "x.txt", "content": "long content", "create": True}
    )
    assert payload(result)["diff_truncated"] is True
    assert len(payload(result)["diff"]) == 10
    assert (tmp_path / "x.txt").read_text(encoding="utf-8") == "long content"


@pytest.mark.asyncio
async def test_internal_area_hidden_from_all_model_file_tools(tmp_path: Path) -> None:
    internal = tmp_path / ".netstudio" / "checkpoints"
    internal.mkdir(parents=True)
    (internal / "secret.json").write_text("INTERNAL_SECRET", encoding="utf-8")
    listing = await ListFilesTool(tmp_path).execute({"recursive": True})
    search = await SearchTextTool(tmp_path).execute({"query": "INTERNAL_SECRET"})
    read = await ReadFileTool(tmp_path).execute({"path": ".netstudio/checkpoints/secret.json"})
    write = await WriteFileTool(tmp_path).execute(
        {"path": ".netstudio/user.txt", "content": "x", "create": True}
    )
    assert ".netstudio" not in listing.output
    assert "INTERNAL_SECRET" not in search.output
    failure(read, "reserved_internal_path")
    failure(write, "reserved_internal_path")


def registry(tmp_path: Path) -> ToolRegistry:
    value = ToolRegistry()
    for tool in [
        ShellTool(tmp_path),
        ReadFileTool(tmp_path),
        ListFilesTool(tmp_path),
        SearchTextTool(tmp_path),
        WriteFileTool(tmp_path),
    ]:
        value.register(tool)
    return value


def context(tmp_path: Path, *capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        scope=ScopeRef("test", workspace_root=tmp_path),
        policy=PolicySnapshot(frozenset(capabilities)),
    )


def test_registry_keeps_read_and_write_separate(tmp_path: Path) -> None:
    value = registry(tmp_path)
    assert value.view(context(tmp_path)).names() == ()
    assert value.view(context(tmp_path, ToolCapability.WRITE)).names() == ("write_file",)
    assert value.view(context(tmp_path, ToolCapability.READ)).names() == (
        "read_file",
        "list_files",
        "search_text",
    )
    assert value.view(context(tmp_path, ToolCapability.READ, ToolCapability.WRITE)).names() == (
        "read_file",
        "list_files",
        "search_text",
        "write_file",
    )
