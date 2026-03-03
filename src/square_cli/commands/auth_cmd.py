"""Authentication commands: login, logout, status."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from .. import auth as auth_module
from .. import config as cfg

app = typer.Typer(help="Authentication commands.", no_args_is_help=False, invoke_without_command=True)
console = Console()


@app.command()
def login(
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Authenticate against sandbox")] = False,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """Authenticate with Square via OAuth browser flow."""
    result = auth_module.login(profile=profile, sandbox=sandbox)

    merchant = result.get("merchant_id", "Unknown")
    env = result.get("environment", "production")

    console.print()
    console.print(f"[bold green]Authenticated![/]")
    console.print(f"  Merchant:    {merchant}")
    console.print(f"  Environment: {env}")
    console.print(f"  Profile:     {result['profile']}")
    console.print(f"  Credentials stored in OS keychain.")
    console.print()
    console.print(
        '[dim]Tip: Run "square locations list" to see your locations, then\n'
        '     "square locations set-default <id>" to set a default.[/]'
    )


@app.command()
def logout(
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """Clear stored credentials."""
    auth_module.logout(profile=profile)


@app.command()
def status(
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """Show current authentication state."""
    token = cfg.get_access_token(profile)
    profile_cfg = cfg.load_config(profile=profile)

    console.print()
    if token:
        # Mask the token for display
        masked = token[:8] + "..." + token[-4:] if len(token) > 16 else "****"
        console.print(f"[bold green]Authenticated[/]")
        console.print(f"  Profile:     {profile}")
        console.print(f"  Environment: {cfg.get_environment(profile_cfg)}")
        console.print(f"  Location:    {profile_cfg.get('location_id') or '[dim]not set[/]'}")
        console.print(f"  Merchant:    {profile_cfg.get('merchant_id', '[dim]unknown[/]')}")
        console.print(f"  Token:       {masked}")

        # Check if token is from env var
        import os

        if os.environ.get("SQUARE_ACCESS_TOKEN"):
            console.print(f"  Source:      SQUARE_ACCESS_TOKEN env var")
        else:
            console.print(f"  Source:      OS keychain")
    else:
        console.print("[bold red]Not authenticated[/]")
        console.print(
            '\n  Run "square login" to authenticate, or set SQUARE_ACCESS_TOKEN.'
        )
    console.print()
