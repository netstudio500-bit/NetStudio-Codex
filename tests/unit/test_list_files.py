"""Behavioral and security tests for ListFilesTool."""

import json
import os
from pathlib import Path

import pytest

from netstudio.runtime import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools import (
    DEFAULT_MAX_ENTRIES,
    ListFilesTool,
    ReadFileTool,
    ShellTool,
    ToolRegistry,
)


def entries(result) -> list[dict[str, str]]:
    """Decode structured list_files output."""
    return json.loads(result.output)["entries"]


def assert_failure(result, code: str) -> None:
    """Assert one stable list_files failure code."""
    assert result.success is False
    assert result.metadata["code"] == code
    assert result.error


def make_symlink(link: Path, target: Path, directory: bool = False) -> None:
    """Create a real symlink or skip only for a genuine Windows privilege failure."""
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if os.name == "nt":
            pytest.skip(f"Windows host does not grant symlink creation privilege: {exc}")
        raise


def test_list_files_metadata_declares_read_contract_and_defaults(tmp_path: Path) -> None:
    metadata = ListFilesTool(tmp_path).metadata

    assert metadata.name == "list_files"
    assert metadata.capabilities == frozenset({ToolCapability.READ})
    assert metadata.argument_schema == {
        "type": "object",
        "properties": {
            "path": {"type": "string", "minLength": 1, "default": "."},
            "recursive": {"type": "boolean", "default": False},
        },
        "additionalProperties": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({"path": 42}, "path must be a string"),
        ({"path": "  "}, "path must not be empty"),
        ({"recursive": 1}, "recursive must be a boolean"),
        ({"recursive": 0}, "recursive must be a boolean"),
        ({"recursive": "false"}, "recursive must be a boolean"),
        ({"extra": True}, "Unsupported arguments: extra"),
    ],
)
async def test_list_files_rejects_invalid_arguments(
    tmp_path: Path, arguments: dict[str, object], message: str
) -> None:
    result = await ListFilesTool(tmp_path).execute(arguments)

    assert_failure(result, "invalid_arguments")
    assert result.error == message


@pytest.mark.asyncio
async def test_list_files_defaults_to_non_recursive_workspace_root(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a-dir").mkdir()
    (tmp_path / "a-dir" / "nested.txt").write_text("nested", encoding="utf-8")

    result = await ListFilesTool(tmp_path).execute({})

    assert result.success is True
    assert entries(result) == [
        {"path": "a-dir", "type": "directory"},
        {"path": "b.txt", "type": "file"},
    ]
    assert result.metadata == {
        "root": ".",
        "recursive": False,
        "count": 2,
        "truncated": False,
    }


@pytest.mark.asyncio
async def test_list_files_recurses_with_relative_deterministic_paths(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("z", encoding="utf-8")
    source = tmp_path / "src"
    source.mkdir()
    (source / "module.txt").write_text("module", encoding="utf-8")
    (source / "a.txt").write_text("a", encoding="utf-8")

    result = await ListFilesTool(tmp_path).execute({"path": ".", "recursive": True})

    listed = entries(result)
    assert listed == [
        {"path": "src", "type": "directory"},
        {"path": "src/a.txt", "type": "file"},
        {"path": "src/module.txt", "type": "file"},
        {"path": "z.txt", "type": "file"},
    ]
    assert [entry["path"] for entry in listed] == sorted(entry["path"] for entry in listed)
    assert all(not Path(entry["path"]).is_absolute() for entry in listed)
    assert result.metadata["recursive"] is True
    assert result.metadata["count"] == 4
    assert result.metadata["truncated"] is False


@pytest.mark.asyncio
async def test_list_files_uses_requested_directory_as_root(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "module.txt").write_text("module", encoding="utf-8")

    result = await ListFilesTool(tmp_path).execute({"path": "src"})

    assert entries(result) == [{"path": "src/module.txt", "type": "file"}]
    assert result.metadata["root"] == "src"


@pytest.mark.asyncio
async def test_list_files_rejects_missing_root(tmp_path: Path) -> None:
    result = await ListFilesTool(tmp_path).execute({"path": "missing"})

    assert_failure(result, "path_not_found")


@pytest.mark.asyncio
async def test_list_files_rejects_file_as_root(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("file", encoding="utf-8")

    result = await ListFilesTool(tmp_path).execute({"path": "file.txt"})

    assert_failure(result, "not_a_directory")


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", ["../secret", "nested/../../secret"])
async def test_list_files_blocks_traversal(tmp_path: Path, requested: str) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "secret").mkdir()

    result = await ListFilesTool(workspace).execute({"path": requested})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_list_files_blocks_external_absolute_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()

    result = await ListFilesTool(workspace).execute({"path": str(external.resolve())})

    assert_failure(result, "path_outside_workspace")


@pytest.mark.asyncio
async def test_list_files_truncates_deterministically_at_explicit_limit(tmp_path: Path) -> None:
    for name in ["z.txt", "a.txt", "m.txt", "b.txt"]:
        (tmp_path / name).write_text(name, encoding="utf-8")

    result = await ListFilesTool(tmp_path, max_entries=2).execute({"recursive": True})

    assert entries(result) == [
        {"path": "a.txt", "type": "file"},
        {"path": "b.txt", "type": "file"},
    ]
    assert result.metadata == {
        "root": ".",
        "recursive": True,
        "count": 2,
        "truncated": True,
    }


def test_default_list_files_limit_is_explicit() -> None:
    assert DEFAULT_MAX_ENTRIES == 1000


@pytest.mark.asyncio
async def test_list_files_reports_internal_file_symlink_explicitly(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("inside", encoding="utf-8")
    make_symlink(tmp_path / "link.txt", target)

    result = await ListFilesTool(tmp_path).execute({})

    assert {"path": "link.txt", "type": "symlink"} in entries(result)


@pytest.mark.asyncio
async def test_list_files_does_not_follow_internal_directory_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real-dir"
    target.mkdir()
    (target / "nested-secret.txt").write_text("inside", encoding="utf-8")
    make_symlink(tmp_path / "dir-link", target, directory=True)

    result = await ListFilesTool(tmp_path).execute({"recursive": True})

    listed = entries(result)
    assert {"path": "dir-link", "type": "symlink"} in listed
    assert all(not entry["path"].startswith("dir-link/") for entry in listed)


@pytest.mark.asyncio
async def test_list_files_external_file_symlink_never_exposes_target(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = tmp_path / "secret.txt"
    secret.write_text("EXTERNAL_SECRET", encoding="utf-8")
    make_symlink(workspace / "external-file", secret)

    result = await ListFilesTool(workspace).execute({"recursive": True})

    assert entries(result) == [{"path": "external-file", "type": "symlink"}]
    assert "EXTERNAL_SECRET" not in result.output
    assert str(secret.resolve()) not in result.output


@pytest.mark.asyncio
async def test_list_files_external_directory_symlink_is_not_traversed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    (external / "secret.txt").write_text("EXTERNAL_SECRET", encoding="utf-8")
    make_symlink(workspace / "external-dir", external, directory=True)

    result = await ListFilesTool(workspace).execute({"recursive": True})

    assert entries(result) == [{"path": "external-dir", "type": "symlink"}]
    assert "secret.txt" not in result.output
    assert "EXTERNAL_SECRET" not in result.output
    assert str(external.resolve()) not in result.output


@pytest.mark.asyncio
async def test_list_files_blocks_external_symlink_used_as_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    make_symlink(workspace / "external-root", external, directory=True)

    result = await ListFilesTool(workspace).execute({"path": "external-root"})

    assert_failure(result, "path_outside_workspace")


def registry_with_file_tools(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ShellTool(tmp_path))
    registry.register(ReadFileTool(tmp_path))
    registry.register(ListFilesTool(tmp_path))
    return registry


def context(tmp_path: Path, *capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        scope=ScopeRef("test", workspace_root=tmp_path),
        policy=PolicySnapshot(frozenset(capabilities)),
    )


def test_registry_hides_file_tools_with_empty_policy(tmp_path: Path) -> None:
    assert registry_with_file_tools(tmp_path).view(context(tmp_path)).names() == ()


def test_local_execution_does_not_permit_file_tools(tmp_path: Path) -> None:
    assert registry_with_file_tools(tmp_path).view(
        context(tmp_path, ToolCapability.LOCAL_EXECUTION)
    ).names() == ("shell",)


def test_read_permits_both_file_tools_and_not_shell(tmp_path: Path) -> None:
    assert registry_with_file_tools(tmp_path).view(
        context(tmp_path, ToolCapability.READ)
    ).names() == (
        "read_file",
        "list_files",
    )
