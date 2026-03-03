"""Raw HTTP commands: get, post, delete."""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.syntax import Syntax

from ..client import get_client
from ..errors import exit_with_error

app = typer.Typer(help="Raw HTTP commands.")
console = Console()

SQUARE_BASE_URL = "https://connect.squareup.com"
SQUARE_SANDBOX_URL = "https://connect.squareupsandbox.com"


def _make_request(method: str, path: str, data: str | None, show_headers: bool,
                  access_token: str | None, profile: str, sandbox: bool) -> None:
    """Execute a raw HTTP request against the Square API."""
    import httpx

    from .. import config as cfg
    from ..errors import AuthError

    token = access_token or cfg.get_access_token(profile)
    if not token:
        exit_with_error(
            "Not authenticated.",
            hint='Run "square login" to authenticate, or set SQUARE_ACCESS_TOKEN.',
        )

    base = SQUARE_SANDBOX_URL if sandbox else SQUARE_BASE_URL
    url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = None
    if data:
        try:
            body = json.loads(data)
        except json.JSONDecodeError:
            exit_with_error("Invalid JSON in --data.", hint="Ensure the JSON is valid.")

    try:
        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, json=body, timeout=30)
    except httpx.RequestError as e:
        exit_with_error(f"Request failed: {e}")

    if show_headers:
        console.print(f"[bold]HTTP {response.status_code}[/]")
        for k, v in response.headers.items():
            console.print(f"  {k}: {v}")
        console.print()

    try:
        result = response.json()
        formatted = json.dumps(result, indent=2, default=str)
        syntax = Syntax(formatted, "json", theme="monokai")
        console.print(syntax)
    except (json.JSONDecodeError, ValueError):
        console.print(response.text)

    if response.status_code >= 400:
        raise typer.Exit(1)


@app.command("get")
def http_get(
    path: Annotated[str, typer.Argument(help="API path (e.g., /v2/catalog/list)")],
    show_headers: Annotated[bool, typer.Option("--show-headers", help="Show response headers")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Make a raw GET request to the Square API."""
    _make_request("GET", path, None, show_headers, access_token, profile, sandbox)


@app.command("post")
def http_post(
    path: Annotated[str, typer.Argument(help="API path (e.g., /v2/catalog/search)")],
    data: Annotated[Optional[str], typer.Option("--data", "-d", help="JSON request body")] = None,
    show_headers: Annotated[bool, typer.Option("--show-headers", help="Show response headers")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Make a raw POST request to the Square API."""
    _make_request("POST", path, data, show_headers, access_token, profile, sandbox)


@app.command("delete")
def http_delete(
    path: Annotated[str, typer.Argument(help="API path (e.g., /v2/catalog/object/XXX)")],
    show_headers: Annotated[bool, typer.Option("--show-headers", help="Show response headers")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Make a raw DELETE request to the Square API."""
    _make_request("DELETE", path, None, show_headers, access_token, profile, sandbox)
