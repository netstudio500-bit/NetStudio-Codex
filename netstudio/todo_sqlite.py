"""SQLite-backed Todo store.

Provides a lightweight SQLite implementation for the TodoStore API used in
examples, with safe defaults for local use. Uses WAL journaling to improve
concurrency for simple multi-process access.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4


@dataclass
class Todo:
    id: str
    text: str
    done: bool
    created_at: str
    updated_at: str


class TodoSQLiteStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or Path("~/.netstudio_todos.db")).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # connect with check_same_thread=False to allow access from other threads
        # use isolation_level=None for autocommit mode but we will manage transactions
        self.conn = sqlite3.connect(str(self.path), timeout=10, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        # Enable WAL for better concurrency
        try:
            self.conn.execute("PRAGMA journal_mode=WAL;")
        except sqlite3.DatabaseError:
            pass
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    text TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass

    def list(self) -> List[Todo]:
        cur = self.conn.execute("SELECT id, text, done, created_at, updated_at FROM todos ORDER BY created_at DESC")
        rows = cur.fetchall()
        return [Todo(id=r["id"], text=r["text"], done=bool(r["done"]), created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]

    def add(self, text: str) -> Todo:
        now = datetime.utcnow().isoformat() + "Z"
        tid = str(uuid4())
        with self.conn:
            self.conn.execute(
                "INSERT INTO todos (id, text, done, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (tid, text, 0, now, now),
            )
        return Todo(id=tid, text=text, done=False, created_at=now, updated_at=now)

    def get(self, todo_id: str) -> Optional[Todo]:
        cur = self.conn.execute(
            "SELECT id, text, done, created_at, updated_at FROM todos WHERE id = ?", (todo_id,)
        )
        r = cur.fetchone()
        if not r:
            return None
        return Todo(id=r["id"], text=r["text"], done=bool(r["done"]), created_at=r["created_at"], updated_at=r["updated_at"]) 

    def update(self, todo_id: str, text: Optional[str] = None, done: Optional[bool] = None) -> Optional[Todo]:
        # Build dynamic SQL
        updates = []
        params = []
        if text is not None:
            updates.append("text = ?")
            params.append(text)
        if done is not None:
            updates.append("done = ?")
            params.append(1 if done else 0)
        if not updates:
            return None
        now = datetime.utcnow().isoformat() + "Z"
        updates.append("updated_at = ?")
        params.append(now)
        params.append(todo_id)
        sql = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
        with self.conn:
            cur = self.conn.execute(sql, tuple(params))
            if cur.rowcount == 0:
                return None
        return self.get(todo_id)

    def delete(self, todo_id: str) -> bool:
        with self.conn:
            cur = self.conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            return cur.rowcount > 0
