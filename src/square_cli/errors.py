"""Error handling for Square CLI."""

from __future__ import annotations

import sys

from rich.console import Console

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


class APIError(SquareCLIError):
    """Square API returned an error."""

    def __init__(self, message: str, errors: list[dict] | None = None, hint: str | None = None):
        self.api_errors = errors or []
        super().__init__(message, hint)


def handle_api_result(result: object) -> dict:
    """Process a Square API result, raising on errors.

    The Square Python SDK returns result objects with .is_success(),
    .body (dict), and .errors (list of error dicts).
    """
    if result.is_success():
        return result.body

    errors = result.errors or []
    messages = []
    for err in errors:
        code = err.get("code", "UNKNOWN")
        detail = err.get("detail", "No details provided")
        field = err.get("field")
        msg = f"{code}: {detail}"
        if field:
            msg += f" (field: {field})"
        messages.append(msg)

    error_text = "; ".join(messages) if messages else "Unknown API error"
    raise APIError(error_text, errors=errors)


def print_error(message: str, hint: str | None = None) -> None:
    """Print a formatted error message to stderr."""
    console.print(f"[bold red]Error:[/] {message}")
    if hint:
        console.print(f"  [dim]Hint: {hint}[/]")


def exit_with_error(message: str, hint: str | None = None, code: int = 1) -> None:
    """Print error and exit."""
    print_error(message, hint)
    sys.exit(code)
