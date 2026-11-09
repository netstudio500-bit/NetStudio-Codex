"""Simple file-based Todo store (local storage on disk).

This provides a lightweight API for storing todos in a JSON file. Each todo is
an object with id, text, done, created_at, updated_at.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
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

    @classmethod
    def create(cls, text: str) -> "Todo":
        now = datetime.utcnow().isoformat() + "Z"
        return cls(id=str(uuid4()), text=text, done=False, created_at=now, updated_at=now)


class TodoStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or Path("~/.netstudio_todos.json").expanduser())
        self._ensure_file()

    def _ensure_file(self) -> None:
        if not self.path.exists():
            self._write_data([])

    def _read_data(self) -> List[dict]:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_data(self, data: List[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def list(self) -> List[Todo]:
        raw = self._read_data()
        return [Todo(**r) for r in raw]

    def add(self, text: str) -> Todo:
        todo = Todo.create(text)
        data = self._read_data()
        data.insert(0, asdict(todo))
        self._write_data(data)
        return todo

    def get(self, todo_id: str) -> Optional[Todo]:
        for r in self._read_data():
            if r.get("id") == todo_id:
                return Todo(**r)
        return None

    def update(self, todo_id: str, text: Optional[str] = None, done: Optional[bool] = None) -> Optional[Todo]:
        data = self._read_data()
        changed = False
        for r in data:
            if r.get("id") == todo_id:
                if text is not None:
                    r["text"] = text
                    changed = True
                if done is not None:
                    r["done"] = bool(done)
                    changed = True
                if changed:
                    r["updated_at"] = datetime.utcnow().isoformat() + "Z"
                break
        if changed:
            self._write_data(data)
            return Todo(**r)
        return None

    def delete(self, todo_id: str) -> bool:
        data = self._read_data()
        new = [r for r in data if r.get("id") != todo_id]
        if len(new) == len(data):
            return False
        self._write_data(new)
        return True
