"""Error handling for Square CLI."""

from __future__ import annotations

import sys

from rich.console import Console
from square.core.api_error import ApiError

console = Console(stderr=True)


class SquareCLIError(Exception):
    """Base error for Square CLI."""

    def __init__(self, message: str, hint: str | None = None):
        self.message = message
        self.hint = hint
        super().__init__(message)


class AuthError(SquareCLIError):
    """Authentication error."""

    pass


class NotFoundError(SquareCLIError):
    """Resource not found."""

    pass


def format_api_error(err: ApiError) -> str:
    """Format a Square API error for display."""
    if hasattr(err, 'body') and isinstance(err.body, dict):
        errors = err.body.get("errors", [])
        messages = []
        for e in errors:
            code = e.get("code", "UNKNOWN")
            detail = e.get("detail", "No details provided")
            field = e.get("field")
            msg = f"{code}: {detail}"
            if field:
                msg += f" (field: {field})"
            messages.append(msg)
        if messages:
            return "; ".join(messages)
    return str(err)


def print_error(message: str, hint: str | None = None) -> None:
    """Print a formatted error message to stderr."""
    console.print(f"[bold red]Error:[/] {message}")
    if hint:
        console.print(f"  [dim]Hint: {hint}[/]")


def exit_with_error(message: str, hint: str | None = None, code: int = 1) -> None:
    """Print error and exit."""
    print_error(message, hint)
    sys.exit(code)
