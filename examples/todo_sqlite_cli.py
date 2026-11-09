#!/usr/bin/env python3
"""CLI for the SQLite-backed Todo store.

Usage: python examples/todo_sqlite_cli.py
Commands mirror examples/todo_cli.py but store in a local SQLite file.
"""
import argparse
from pathlib import Path

from netstudio.todo_sqlite import TodoSQLiteStore


def cmd_add(args):
    store = TodoSQLiteStore(path=Path(args.db) if args.db else None)
    todo = store.add(args.text)
    print(f"Added: {todo.id} - {todo.text}")


def cmd_list(args):
    store = TodoSQLiteStore(path=Path(args.db) if args.db else None)
    items = store.list()
    if not items:
        print("No todos found.")
        return
    for t in items:
        status = "x" if t.done else " "
        print(f"[{status}] {t.id} - {t.text}")


def cmd_done(args):
    store = TodoSQLiteStore(path=Path(args.db) if args.db else None)
    updated = store.update(args.id, done=True)
    if updated:
        print(f"Marked done: {updated.id}")
    else:
        print("Todo not found")


def cmd_rm(args):
    store = TodoSQLiteStore(path=Path(args.db) if args.db else None)
    ok = store.delete(args.id)
    print("Deleted" if ok else "Todo not found")


def cmd_edit(args):
    store = TodoSQLiteStore(path=Path(args.db) if args.db else None)
    updated = store.update(args.id, text=args.text)
    if updated:
        print(f"Updated: {updated.id} - {updated.text}")
    else:
        print("Todo not found or no change")


def main():
    parser = argparse.ArgumentParser(prog="todo-sqlite", description="Simple SQLite-backed todo CLI")
    parser.add_argument("--db", help="Path to SQLite DB file (default: ~/.netstudio_todos.db)")
    sub = parser.add_subparsers(dest="cmd")

    a = sub.add_parser("add")
    a.add_argument("text")
    a.set_defaults(func=cmd_add)

    l = sub.add_parser("list")
    l.set_defaults(func=cmd_list)

    d = sub.add_parser("done")
    d.add_argument("id")
    d.set_defaults(func=cmd_done)

    r = sub.add_parser("rm")
    r.add_argument("id")
    r.set_defaults(func=cmd_rm)

    e = sub.add_parser("edit")
    e.add_argument("id")
    e.add_argument("text")
    e.set_defaults(func=cmd_edit)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
