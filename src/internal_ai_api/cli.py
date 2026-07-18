from __future__ import annotations

import argparse
import json
import sys

from .config import load_settings
from .db import Database


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Manage hashed internal API keys")
    root.add_argument(
        "--platform", required=True, choices=["grok", "gemini", "chatgpt-image"]
    )
    commands = root.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a key; plaintext is printed only once")
    create.add_argument("--owner", required=True)
    create.add_argument("--department")
    create.add_argument("--expires-at", help="ISO-8601 UTC timestamp")

    commands.add_parser("list", help="List key metadata (never plaintext keys)")
    for name in ("enable", "disable"):
        command = commands.add_parser(name)
        command.add_argument("key_id")
    return root


def main() -> None:
    args = parser().parse_args()
    settings = load_settings(args.platform)
    database = Database(settings.db_path)
    if args.command == "create":
        value = database.create_api_key(args.owner, args.department, args.expires_at)
        print(value)
        print("Store this key now. It cannot be recovered from SQLite.", file=sys.stderr)
    elif args.command == "list":
        print(json.dumps(database.list_keys(), ensure_ascii=False, indent=2))
    else:
        changed = database.set_key_enabled(args.key_id, args.command == "enable")
        if not changed:
            raise SystemExit(f"key not found: {args.key_id}")


if __name__ == "__main__":
    main()

