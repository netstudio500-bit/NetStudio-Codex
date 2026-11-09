import json
from pathlib import Path

import pytest

from netstudio.todo import TodoStore


def test_todo_store_add_list(tmp_path):
    p = tmp_path / "todos.json"
    store = TodoStore(path=p)
    assert store.list() == []
    t = store.add("Buy milk")
    assert t.text == "Buy milk"
    items = store.list()
    assert len(items) == 1
    assert items[0].id == t.id


def test_update_and_delete(tmp_path):
    p = tmp_path / "todos.json"
    store = TodoStore(path=p)
    t = store.add("Task A")
    store.update(t.id, done=True)
    got = store.get(t.id)
    assert got and got.done is True
    ok = store.delete(t.id)
    assert ok is True
    assert store.get(t.id) is None
