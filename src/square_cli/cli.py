"""Square CLI — manage your Square business from the command line."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from . import __version__
from .commands import auth_cmd, catalog, config_cmd, utility
from .errors import AuthError, APIError, SquareCLIError, print_error

console = Console()

app = typer.Typer(
    name="square",
    help="A CLI for Square — manage catalog, sales, inventory, customers, and more.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


# --- Register command groups ---

# Auth (top-level: square login, square logout, square status)
app.command("login")(auth_cmd.login)
app.command("logout")(auth_cmd.logout)
app.command("status")(auth_cmd.status)

# Config
app.add_typer(config_cmd.app, name="config")

# Catalog
app.add_typer(catalog.app, name="catalog")

# Utility (top-level: square version, square resources, etc.)
app.command("version")(utility.version)
app.command("resources")(utility.resources)
app.command("docs")(utility.docs)
app.command("feedback")(utility.feedback)


# --- Version callback ---

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"square-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Show version and exit.", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Square CLI — manage your Square business from the command line."""
    pass
