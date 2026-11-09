from pathlib import Path

import pytest

from netstudio.todo_sqlite import TodoSQLiteStore


def test_sqlite_store_add_list(tmp_path):
    p = tmp_path / "todos.db"
    store = TodoSQLiteStore(path=p)
    try:
        assert store.list() == []
        t = store.add("Buy milk")
        assert t.text == "Buy milk"
        items = store.list()
        assert len(items) == 1
        assert items[0].id == t.id
    finally:
        store.close()


def test_update_and_delete(tmp_path):
    p = tmp_path / "todos.db"
    store = TodoSQLiteStore(path=p)
    try:
        t = store.add("Task A")
        store.update(t.id, done=True)
        got = store.get(t.id)
        assert got and got.done is True
        ok = store.delete(t.id)
        assert ok is True
        assert store.get(t.id) is None
    finally:
        store.close()
