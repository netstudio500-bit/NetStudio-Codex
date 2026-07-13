"""Behavioral and security tests for ReadFileTool."""

import os
from pathlib import Path

import pytest

from netstudio.runtime import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools import DEFAULT_MAX_FILE_SIZE_BYTES, ReadFileTool, ToolRegistry


def assert_failure(result, code: str) -> None:
    """Assert one stable read_file failure code."""
    assert result.success is False
    assert result.metadata["code"] == code
    assert result.error


def test_read_file_metadata_declares_read_only_contract(tmp_path: Path) -> None:
    metadata = ReadFileTool(tmp_path).metadata

    assert metadata.name == "read_file"
    assert metadata.capabilities == frozenset({ToolCapability.READ})
    assert metadata.argument_schema == {
        "type": "object",
        "properties": {"path": {"type": "string", "minLength": 1}},
        "required": ["path"],
        "additionalProperties": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "path is required"),
        ({"path": 42}, "path must be a string"),
        ({"path": "  "}, "path must not be empty"),
        ({"path": "file.txt", "extra": True}, "Unsupported arguments: extra"),
    ],
)
async def test_read_file_rejects_invalid_arguments(
    tmp_path: Path, arguments: dict[str, object], message: str
) -> None:
    result = await ReadFileTool(tmp_path).execute(arguments)

    assert_failure(result, "invalid_arguments")
    assert result.error == message


@pytest.mark.asyncio
async def test_read_file_returns_utf8_content_and_metadata(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "arquivo.txt"
    target.parent.mkdir()
    content = "READ_FILE_OK café 日本語"
    target.write_text(content, encoding="utf-8")

    result = await ReadFileTool(tmp_path).execute({"path": "nested/arquivo.txt"})

    assert result.success is True
    assert result.output == content
    assert result.metadata == {
        "path": "nested/arquivo.txt",
        "size": len(content.encode("utf-8")),
        "encoding": "utf-8",
    }


@pytest.mark.asyncio
async def test_read_file_rejects_missing_file(tmp_path: Path) -> None:
    result = await ReadFileTool(tmp_path).execute({"path": "missing.txt"})

    assert_failure(result, "file_not_found")


@pytest.mark.asyncio
async def test_read_file_rejects_directory(tmp_path: Path) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()

    result = await ReadFileTool(tmp_path).execute({"path": "directory"})

    assert_failure(result, "not_a_file")


@pytest.mark.asyncio
async def test_read_file_blocks_parent_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")

    result = await ReadFileTool(workspace).execute({"path": "../secret.txt"})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_read_file_blocks_external_absolute_path(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET", encoding="utf-8")

    result = await ReadFileTool(workspace).execute({"path": str(secret.resolve())})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_read_file_blocks_mixed_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "secret.txt").write_text("SECRET", encoding="utf-8")

    result = await ReadFileTool(workspace).execute({"path": "nested/../../secret.txt"})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_read_file_blocks_symlink_resolving_outside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET", encoding="utf-8")
    link = workspace / "external-link.txt"
    try:
        link.symlink_to(secret)
    except OSError as exc:
        if os.name == "nt":
            pytest.skip(f"Windows host does not grant symlink creation privilege: {exc}")
        raise

    result = await ReadFileTool(workspace).execute({"path": "external-link.txt"})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_read_file_rejects_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "binary.txt").write_bytes(b"\xff\xfe\xfa")

    result = await ReadFileTool(tmp_path).execute({"path": "binary.txt"})

    assert_failure(result, "invalid_utf8")


@pytest.mark.asyncio
async def test_read_file_rejects_file_above_limit(tmp_path: Path) -> None:
    target = tmp_path / "large.txt"
    target.write_bytes(b"x" * 11)

    result = await ReadFileTool(tmp_path, max_file_size_bytes=10).execute({"path": "large.txt"})

    assert_failure(result, "file_too_large")


def test_default_read_file_limit_is_explicit() -> None:
    assert DEFAULT_MAX_FILE_SIZE_BYTES == 1024 * 1024


def test_registry_hides_read_file_without_read_capability(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(ReadFileTool(tmp_path))
    context = ExecutionContext(scope=ScopeRef("test", workspace_root=tmp_path))

    assert registry.view(context).names() == ()


def test_registry_exposes_read_file_with_read_capability(tmp_path: Path) -> None:
    registry = ToolRegistry()
    registry.register(ReadFileTool(tmp_path))
    context = ExecutionContext(
        scope=ScopeRef("test", workspace_root=tmp_path),
        policy=PolicySnapshot(frozenset({ToolCapability.READ})),
    )

    assert registry.view(context).names() == ("read_file",)
