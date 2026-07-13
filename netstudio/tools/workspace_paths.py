"""Shared workspace path controls for model-facing file tools."""

from pathlib import Path

INTERNAL_DIRECTORY_NAME = ".netstudio"


def is_internal_path(workspace_root: Path, path: Path) -> bool:
    """Return whether a canonical workspace path is in the reserved internal area."""
    internal_root = (workspace_root / INTERNAL_DIRECTORY_NAME).resolve(strict=False)
    resolved = path.resolve(strict=False)
    return resolved == internal_root or resolved.is_relative_to(internal_root)
