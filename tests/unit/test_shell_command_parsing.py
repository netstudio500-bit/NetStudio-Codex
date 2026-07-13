"""Cross-platform command parsing behavior for ShellTool."""

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from netstudio.tools import ShellTool


def command_with_argument(script: str, argument: str) -> str:
    """Serialize argv using the platform's supported command-line convention."""
    argv = [sys.executable, "-c", script, argument]
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


@pytest.mark.asyncio
async def test_shell_preserves_quoted_argument_containing_spaces(tmp_path: Path) -> None:
    result = await ShellTool(tmp_path).execute(
        {"command": command_with_argument("import sys; print(sys.argv[1])", "argument with spaces")}
    )

    assert result.success is True
    assert result.output.strip() == "argument with spaces"
    assert result.metadata["exit_code"] == 0
