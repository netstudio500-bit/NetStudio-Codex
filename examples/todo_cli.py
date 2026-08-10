#!/usr/bin/env python3
"""Simple CLI for the Todo store.

Usage:
  python examples/todo_cli.py add "Buy milk"
  python examples/todo_cli.py list
  python examples/todo_cli.py done <id>
  python examples/todo_cli.py rm <id>
  python examples/todo_cli.py edit <id> "new text"
"""
import argparse
import textwrap
from pathlib import Path

from netstudio.todo import TodoStore


def cmd_add(args):
    store = TodoStore()
    todo = store.add(args.text)
    print(f"Added: {todo.id} - {todo.text}")


def cmd_list(args):
    store = TodoStore()
    items = store.list()
    if not items:
        print("No todos found.")
        return
    for t in items:
        status = "x" if t.done else " "
        print(f"[{status}] {t.id} - {t.text}")


def cmd_done(args):
    store = TodoStore()
    updated = store.update(args.id, done=True)
    if updated:
        print(f"Marked done: {updated.id}")
    else:
        print("Todo not found")


def cmd_rm(args):
    store = TodoStore()
    ok = store.delete(args.id)
    print("Deleted" if ok else "Todo not found")


def cmd_edit(args):
    store = TodoStore()
    updated = store.update(args.id, text=args.text)
    if updated:
        print(f"Updated: {updated.id} - {updated.text}")
    else:
        print("Todo not found or no change")


def main():
    parser = argparse.ArgumentParser(prog="todo", description="Simple local todo CLI")
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
