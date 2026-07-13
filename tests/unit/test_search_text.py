"""Behavioral and security tests for SearchTextTool."""

import json
import os
from pathlib import Path

import pytest

from netstudio.runtime import ExecutionContext, PolicySnapshot, ScopeRef
from netstudio.runtime.capabilities import ToolCapability
from netstudio.tools import ListFilesTool, ReadFileTool, SearchTextTool, ShellTool, ToolRegistry
from netstudio.tools.search_text import (
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_RESULTS,
    DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES,
)


def matches(result) -> list[dict[str, str | int]]:
    return json.loads(result.output)["matches"]


def assert_failure(result, code: str) -> None:
    assert result.success is False
    assert result.metadata["code"] == code
    assert result.error


def make_symlink(link: Path, target: Path, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as exc:
        if os.name == "nt":
            pytest.skip(f"Windows host does not grant symlink creation privilege: {exc}")
        raise


def test_search_text_metadata_declares_read_contract_and_defaults(tmp_path: Path) -> None:
    metadata = SearchTextTool(tmp_path).metadata

    assert metadata.name == "search_text"
    assert metadata.capabilities == frozenset({ToolCapability.READ})
    assert metadata.argument_schema == {
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "path": {"type": "string", "minLength": 1, "default": "."},
            "case_sensitive": {"type": "boolean", "default": False},
        },
        "required": ["query"],
        "additionalProperties": False,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ({}, "query is required"),
        ({"query": 1}, "query must be a string"),
        ({"query": ""}, "query must not be empty"),
        ({"query": "x", "path": 1}, "path must be a string"),
        ({"query": "x", "path": "  "}, "path must not be empty"),
        ({"query": "x", "case_sensitive": 1}, "case_sensitive must be a boolean"),
        ({"query": "x", "case_sensitive": 0}, "case_sensitive must be a boolean"),
        ({"query": "x", "extra": True}, "Unsupported arguments: extra"),
    ],
)
async def test_search_text_rejects_invalid_arguments(
    tmp_path: Path, arguments: dict[str, object], message: str
) -> None:
    result = await SearchTextTool(tmp_path).execute(arguments)

    assert_failure(result, "invalid_arguments")
    assert result.error == message


@pytest.mark.asyncio
async def test_search_text_searches_individual_file_with_one_based_positions(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("first\nxx token token\n", encoding="utf-8")

    result = await SearchTextTool(tmp_path).execute(
        {"query": "token", "path": "target.txt", "case_sensitive": True}
    )

    assert matches(result) == [
        {"path": "target.txt", "line": 2, "column": 4, "text": "xx token token"},
        {"path": "target.txt", "line": 2, "column": 10, "text": "xx token token"},
    ]
    assert result.metadata["root"] == "target.txt"
    assert result.metadata["truncated"] is False


@pytest.mark.asyncio
async def test_search_text_recurses_in_deterministic_relative_path_order(tmp_path: Path) -> None:
    (tmp_path / "z.txt").write_text("TARGET", encoding="utf-8")
    source = tmp_path / "src"
    source.mkdir()
    (source / "b.txt").write_text("TARGET", encoding="utf-8")
    (source / "a.txt").write_text("TARGET", encoding="utf-8")

    result = await SearchTextTool(tmp_path).execute({"query": "TARGET"})

    listed = matches(result)
    assert [match["path"] for match in listed] == ["src/a.txt", "src/b.txt", "z.txt"]
    assert all(not Path(str(match["path"])).is_absolute() for match in listed)
    assert result.metadata == {
        "query": "TARGET",
        "root": ".",
        "case_sensitive": False,
        "files_examined": 3,
        "matches_count": 3,
        "truncated": False,
        "skipped_invalid_utf8": 0,
        "skipped_too_large": 0,
    }


@pytest.mark.asyncio
async def test_search_text_case_sensitive_and_insensitive(tmp_path: Path) -> None:
    (tmp_path / "case.txt").write_text("Target target", encoding="utf-8")
    tool = SearchTextTool(tmp_path)

    sensitive = await tool.execute({"query": "target", "case_sensitive": True})
    insensitive = await tool.execute({"query": "target"})

    assert [match["column"] for match in matches(sensitive)] == [8]
    assert [match["column"] for match in matches(insensitive)] == [1, 8]


@pytest.mark.asyncio
async def test_search_text_uses_unicode_casefold_and_original_column(tmp_path: Path) -> None:
    (tmp_path / "unicode.txt").write_text("xx Straße yy", encoding="utf-8")

    result = await SearchTextTool(tmp_path).execute({"query": "STRASSE"})

    assert matches(result) == [
        {"path": "unicode.txt", "line": 1, "column": 4, "text": "xx Straße yy"}
    ]


@pytest.mark.asyncio
async def test_search_text_rejects_missing_and_external_paths(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    tool = SearchTextTool(workspace)

    missing = await tool.execute({"query": "x", "path": "missing"})
    traversal = await tool.execute({"query": "x", "path": "nested/../../external"})
    absolute = await tool.execute({"query": "x", "path": str(external.resolve())})

    assert_failure(missing, "path_not_found")
    assert_failure(traversal, "path_outside_workspace")
    assert_failure(absolute, "path_outside_workspace")


@pytest.mark.asyncio
async def test_search_text_skips_invalid_utf8_and_large_files(tmp_path: Path) -> None:
    (tmp_path / "bad.bin").write_bytes(b"TARGET\xff")
    (tmp_path / "large.txt").write_text("TARGET TOO LARGE", encoding="utf-8")
    (tmp_path / "valid.txt").write_text("TARGET", encoding="utf-8")

    result = await SearchTextTool(tmp_path, max_file_size_bytes=8).execute({"query": "TARGET"})

    assert matches(result) == [
        {"path": "valid.txt", "line": 1, "column": 1, "text": "TARGET"}
    ]
    assert result.metadata["skipped_invalid_utf8"] == 1
    assert result.metadata["skipped_too_large"] == 1


@pytest.mark.asyncio
async def test_search_text_file_limit_is_deterministic_and_explicit(tmp_path: Path) -> None:
    for name in ["c.txt", "a.txt", "b.txt"]:
        (tmp_path / name).write_text("TARGET", encoding="utf-8")

    result = await SearchTextTool(tmp_path, max_files=2).execute({"query": "TARGET"})

    assert [match["path"] for match in matches(result)] == ["a.txt", "b.txt"]
    assert result.metadata["files_examined"] == 2
    assert result.metadata["truncated"] is True


@pytest.mark.asyncio
async def test_search_text_result_limit_is_deterministic_and_explicit(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x x x", encoding="utf-8")

    result = await SearchTextTool(tmp_path, max_results=2).execute({"query": "x"})

    assert [match["column"] for match in matches(result)] == [1, 3]
    assert result.metadata["matches_count"] == 2
    assert result.metadata["truncated"] is True


def test_search_text_limits_are_explicit() -> None:
    assert DEFAULT_MAX_FILES == 1000
    assert DEFAULT_MAX_RESULTS == 200
    assert DEFAULT_MAX_SEARCH_FILE_SIZE_BYTES == 1024 * 1024


@pytest.mark.asyncio
async def test_search_text_does_not_follow_internal_file_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("TARGET", encoding="utf-8")
    make_symlink(tmp_path / "link.txt", target)

    result = await SearchTextTool(tmp_path).execute({"query": "TARGET"})

    assert [match["path"] for match in matches(result)] == ["target.txt"]


@pytest.mark.asyncio
async def test_search_text_does_not_follow_internal_directory_symlink(tmp_path: Path) -> None:
    target = tmp_path / "real-dir"
    target.mkdir()
    (target / "target.txt").write_text("TARGET", encoding="utf-8")
    make_symlink(tmp_path / "dir-link", target, directory=True)

    result = await SearchTextTool(tmp_path).execute({"query": "TARGET"})

    assert [match["path"] for match in matches(result)] == ["real-dir/target.txt"]
    assert all(not str(match["path"]).startswith("dir-link/") for match in matches(result))


@pytest.mark.asyncio
async def test_search_text_never_searches_external_symlinks(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external_file = tmp_path / "external.txt"
    external_file.write_text("EXTERNAL_SECRET", encoding="utf-8")
    external_dir = tmp_path / "external-dir"
    external_dir.mkdir()
    (external_dir / "secret.txt").write_text("EXTERNAL_SECRET", encoding="utf-8")
    make_symlink(workspace / "external-file", external_file)
    make_symlink(workspace / "external-dir", external_dir, directory=True)

    result = await SearchTextTool(workspace).execute({"query": "EXTERNAL_SECRET"})

    assert matches(result) == []
    assert str(external_file.resolve()) not in result.output
    assert str(external_dir.resolve()) not in result.output


@pytest.mark.asyncio
async def test_search_text_blocks_external_symlink_used_as_root(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    external = tmp_path / "external"
    external.mkdir()
    make_symlink(workspace / "external-root", external, directory=True)

    result = await SearchTextTool(workspace).execute(
        {"query": "secret", "path": "external-root"}
    )

    assert_failure(result, "path_outside_workspace")


def registry_with_read_tools(tmp_path: Path) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ShellTool(tmp_path))
    registry.register(ReadFileTool(tmp_path))
    registry.register(ListFilesTool(tmp_path))
    registry.register(SearchTextTool(tmp_path))
    return registry


def context(tmp_path: Path, *capabilities: ToolCapability) -> ExecutionContext:
    return ExecutionContext(
        scope=ScopeRef("test", workspace_root=tmp_path),
        policy=PolicySnapshot(frozenset(capabilities)),
    )


def test_registry_policy_filters_search_text_by_read_capability(tmp_path: Path) -> None:
    registry = registry_with_read_tools(tmp_path)

    assert registry.view(context(tmp_path)).names() == ()
    assert registry.view(context(tmp_path, ToolCapability.LOCAL_EXECUTION)).names() == ("shell",)
    assert registry.view(context(tmp_path, ToolCapability.READ)).names() == (
        "read_file",
        "list_files",
        "search_text",
    )
