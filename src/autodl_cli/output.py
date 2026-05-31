from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

SENSITIVE_KEYS = {"root_password", "jupyter_token", "token", "authorization", "password"}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if key.lower() in SENSITIVE_KEYS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def print_json(data: Any) -> None:
    Console().print(json.dumps(redact(data), ensure_ascii=False, indent=2, default=str))


def print_kv(title: str, data: dict[str, Any]) -> None:
    table = Table(title=title, show_header=False)
    table.add_column("Key")
    table.add_column("Value")
    for key, value in redact(data).items():
        table.add_row(str(key), "" if value is None else str(value))
    Console().print(table)


def print_rows(title: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    table = Table(title=title)
    for column in columns:
        table.add_column(column)
    for row in rows:
        redacted = redact(row)
        table.add_row(*["" if redacted.get(column) is None else str(redacted.get(column)) for column in columns])
    Console().print(table)
