"""SQLite-backed persistent conversation memory."""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path
from threading import RLock
from typing import Final


class MemoryRepositoryError(RuntimeError):
    """Base exception for persistent memory failures."""


class InvalidRoleError(MemoryRepositoryError, ValueError):
    """Raised when a message role is not supported."""


class MessageTooLargeError(MemoryRepositoryError, ValueError):
    """Raised when message content exceeds the configured UTF-8 byte limit."""


class MemoryRepository(ABC):
    """Persistence contract consumed by the runtime."""

    @abstractmethod
    def append_message(self, role: str, content: str) -> None:
        """Persist one message for the active session."""

    @abstractmethod
    def close(self) -> None:
        """Release repository resources."""


class MemoryManager(MemoryRepository):
    """Thread-safe SQLite implementation of the runtime memory repository."""

    VALID_ROLES: Final[frozenset[str]] = frozenset(
        {"system", "user", "assistant", "tool"}
    )
    DEFAULT_MAX_MESSAGE_BYTES: Final[int] = 64 * 1024
    DATABASE_FILENAME: Final[str] = "memory.db"

    def __init__(
        self,
        workspace_root: str | Path,
        session_id: str,
        enabled: bool = True,
        *,
        max_message_bytes: int = DEFAULT_MAX_MESSAGE_BYTES,
    ) -> None:
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id must be a non-empty string")
        if isinstance(max_message_bytes, bool) or not isinstance(max_message_bytes, int):
            raise TypeError("max_message_bytes must be an integer")
        if max_message_bytes <= 0:
            raise ValueError("max_message_bytes must be greater than zero")

        self.enabled = enabled
        self.session_id = session_id
        self.max_message_bytes = max_message_bytes
        self._lock = RLock()
        self._closed = False

        self.workspace_root = self._resolve_workspace_root(workspace_root)
        expected_memory_dir = self.workspace_root / "memory" / "persistence"
        self.memory_dir = self._resolve_within_workspace(expected_memory_dir)

        try:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise MemoryRepositoryError(
                f"unable to create memory directory: {self.memory_dir}"
            ) from exc

        self.db_path = self._resolve_within_workspace(
            self.memory_dir / self.DATABASE_FILENAME
        )

        try:
            self._connection = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                isolation_level=None,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._configure_database()
            self._create_schema()
        except sqlite3.Error as exc:
            connection = getattr(self, "_connection", None)
            if connection is not None:
                connection.close()
            raise MemoryRepositoryError(
                f"unable to initialize SQLite memory database: {self.db_path}"
            ) from exc

    @staticmethod
    def _resolve_workspace_root(workspace_root: str | Path) -> Path:
        try:
            root = Path(workspace_root).expanduser().resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise MemoryRepositoryError("workspace_root cannot be resolved") from exc

        if not root.is_dir():
            raise NotADirectoryError(f"workspace_root is not a directory: {root}")
        return root

    def _resolve_within_workspace(self, path: Path) -> Path:
        try:
            resolved = path.resolve(strict=False)
            resolved.relative_to(self.workspace_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise MemoryRepositoryError(
                f"path escapes workspace root: {path}"
            ) from exc
        return resolved

    def _configure_database(self) -> None:
        pragmas = (
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL",
            "PRAGMA foreign_keys=ON",
            "PRAGMA busy_timeout=5000",
        )
        with self._lock:
            for pragma in pragmas:
                self._connection.execute(pragma)

    def _create_schema(self) -> None:
        with self._lock:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (
                        role IN ('system', 'user', 'assistant', 'tool')
                    ),
                    content TEXT NOT NULL,
                    content_bytes INTEGER NOT NULL CHECK (content_bytes >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session_id_id
                    ON messages(session_id, id);
                """
            )

    def append_message(self, role: str, content: str) -> None:
        if not self.enabled:
            return
        if self._closed:
            raise MemoryRepositoryError("memory repository is closed")
        if not isinstance(role, str) or role not in self.VALID_ROLES:
            raise InvalidRoleError(f"unsupported message role: {role!r}")
        if not isinstance(content, str):
            raise TypeError("content must be a string")

        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.max_message_bytes:
            raise MessageTooLargeError(
                "message exceeds UTF-8 byte limit: "
                f"{content_bytes} > {self.max_message_bytes}"
            )

        with self._lock:
            try:
                self._connection.execute("BEGIN IMMEDIATE")
                self._connection.execute(
                    """
                    INSERT INTO messages (
                        session_id,
                        role,
                        content,
                        content_bytes
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (self.session_id, role, content, content_bytes),
                )
                self._connection.commit()
            except sqlite3.Error as exc:
                try:
                    self._connection.rollback()
                except sqlite3.Error:
                    pass
                raise MemoryRepositoryError("unable to persist message") from exc

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._connection.close()
            except sqlite3.Error as exc:
                raise MemoryRepositoryError(
                    "unable to close memory repository"
                ) from exc
            finally:
                self._closed = True

    def __enter__(self) -> MemoryManager:
        if self._closed:
            raise MemoryRepositoryError("memory repository is closed")
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()
