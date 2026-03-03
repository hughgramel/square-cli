"""Output formatting for Square CLI — table, JSON, CSV."""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def format_output(
    data: list[dict[str, Any]],
    columns: list[tuple[str, str]] | None = None,
    fmt: str = "table",
    title: str | None = None,
    summary: str | None = None,
) -> str:
    """Format a list of dicts for output.

    Args:
        data: List of row dicts.
        columns: List of (key, display_label) tuples. If None, inferred from data.
        fmt: Output format — "table", "json", or "csv".
        title: Optional table title.
        summary: Optional summary line printed after table.

    Returns:
        Formatted string.
    """
    if fmt == "json":
        return json.dumps(data, indent=2, default=str)
    elif fmt == "csv":
        return _format_csv(data, columns)
    else:
        return _format_table(data, columns, title, summary)


def print_output(
    data: list[dict[str, Any]],
    columns: list[tuple[str, str]] | None = None,
    fmt: str = "table",
    title: str | None = None,
    summary: str | None = None,
) -> None:
    """Format and print data."""
    if fmt == "json":
        console.print_json(json.dumps(data, default=str))
    elif fmt == "csv":
        console.print(_format_csv(data, columns), highlight=False)
    else:
        _print_table(data, columns, title, summary)


def print_single(data: dict[str, Any], fmt: str = "table", title: str | None = None) -> None:
    """Print a single record."""
    if fmt == "json":
        console.print_json(json.dumps(data, default=str))
    elif fmt == "csv":
        print_output([data], fmt="csv")
    else:
        _print_detail(data, title)


def _infer_columns(data: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Infer columns from the first row."""
    if not data:
        return []
    return [(k, k.replace("_", " ").title()) for k in data[0].keys()]


def _format_csv(data: list[dict[str, Any]], columns: list[tuple[str, str]] | None = None) -> str:
    """Format data as CSV."""
    if not data:
        return ""
    cols = columns or _infer_columns(data)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in cols])
    for row in data:
        writer.writerow([row.get(key, "") for key, _ in cols])
    return buf.getvalue().strip()


def _format_table(
    data: list[dict[str, Any]],
    columns: list[tuple[str, str]] | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> str:
    """Format data as a Rich table string."""
    buf = io.StringIO()
    c = Console(file=buf, force_terminal=True)
    cols = columns or _infer_columns(data)
    table = Table(title=title)
    for _, label in cols:
        table.add_column(label)
    for row in data:
        table.add_row(*[_format_value(row.get(key, "")) for key, _ in cols])
    c.print(table)
    if summary:
        c.print(f"\n{summary}")
    return buf.getvalue()


def _print_table(
    data: list[dict[str, Any]],
    columns: list[tuple[str, str]] | None = None,
    title: str | None = None,
    summary: str | None = None,
) -> None:
    """Print a Rich table to the console."""
    cols = columns or _infer_columns(data)
    table = Table(title=title)
    for key, label in cols:
        justify = "right" if _is_numeric_column(data, key) else "left"
        table.add_column(label, justify=justify)
    for row in data:
        table.add_row(*[_format_value(row.get(key, "")) for key, _ in cols])
    console.print(table)
    if summary:
        console.print(f"\n{summary}")


def _print_detail(data: dict[str, Any], title: str | None = None) -> None:
    """Print a single record as key-value pairs."""
    if title:
        console.print(f"\n[bold]{title}[/]\n")
    max_key = max(len(str(k)) for k in data.keys()) if data else 0
    for key, value in data.items():
        label = key.replace("_", " ").title()
        console.print(f"  {label:<{max_key + 4}} {_format_value(value)}")
    console.print()


def _format_value(value: Any) -> str:
    """Format a value for display."""
    if value is None:
        return "[dim]—[/]"
    if isinstance(value, bool):
        return "[green]Yes[/]" if value else "[red]No[/]"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, default=str)
    return str(value)


def _is_numeric_column(data: list[dict[str, Any]], key: str) -> bool:
    """Check if a column contains numeric data."""
    for row in data:
        v = row.get(key)
        if v is not None and isinstance(v, (int, float)):
            return True
    return False


def format_money(cents: int | None, currency: str = "USD") -> str:
    """Format money amount from cents to dollars."""
    if cents is None:
        return "—"
    dollars = cents / 100
    if currency == "USD":
        return f"${dollars:,.2f}"
    return f"{dollars:,.2f} {currency}"
