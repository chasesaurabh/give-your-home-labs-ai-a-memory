"""Storage-only chapter probe. No model calls and no automatic memory writes."""

import argparse
import json
from pathlib import Path
import sqlite3


def run(database, action, scope, key, value=None):
    if not scope.strip() or not key.strip():
        raise ValueError("Scope and key must be non-empty.")
    if action == "save" and (value is None or not value.strip()):
        raise ValueError("A saved preference needs a non-empty value.")
    path = Path(database)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS memories ("
                "scope TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, "
                "PRIMARY KEY (scope, key))"
            )
            if action == "save":
                connection.execute(
                    "INSERT INTO memories(scope, key, value) VALUES (?, ?, ?) "
                    "ON CONFLICT(scope, key) DO UPDATE SET value=excluded.value",
                    (scope, key, value),
                )
            elif action == "forget":
                connection.execute(
                    "DELETE FROM memories WHERE scope=? AND key=?", (scope, key)
                )
            elif action != "get":
                raise ValueError("Unsupported action.")
            row = connection.execute(
                "SELECT value FROM memories WHERE scope=? AND key=?", (scope, key)
            ).fetchone()
            return {"scope": scope, "key": key, "value": row[0] if row else None}
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("action", choices=("save", "get", "forget"))
    parser.add_argument("--scope", required=True)
    parser.add_argument("--key", required=True)
    parser.add_argument("--value")
    args = parser.parse_args()
    try:
        result = run(args.db, args.action, args.scope, args.key, args.value)
    except (ValueError, sqlite3.Error, OSError) as error:
        parser.exit(2, f"Memory operation failed: {error}\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
