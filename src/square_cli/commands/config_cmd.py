"""Configuration management commands."""

from __future__ import annotations

import os
import subprocess
from typing import Annotated, Optional

import typer
from rich.console import Console

from .. import config as cfg

app = typer.Typer(help="Manage CLI configuration.", no_args_is_help=True)
console = Console()


@app.command("list")
def list_config(
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """View all configuration values."""
    profile_cfg = cfg.load_config(profile=profile)

    console.print(f"\n[bold]Configuration[/] (profile: {profile})\n")
    for key, value in sorted(profile_cfg.items()):
        console.print(f"  {key:<20} {value}")
    console.print(f"\n  [dim]Config file: {cfg.config_path()}[/]")
    console.print()


@app.command("set")
def set_config(
    key: Annotated[str, typer.Argument(help="Config key to set")],
    value: Annotated[str, typer.Argument(help="Value to set")],
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """Set a configuration value."""
    cfg.save_config({key: value}, profile=profile)
    console.print(f'Set {key} = "{value}" in profile "{profile}".')


@app.command("unset")
def unset_config(
    key: Annotated[str, typer.Argument(help="Config key to remove")],
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile name")] = "default",
) -> None:
    """Remove a configuration value."""
    if cfg.unset_config(key, profile=profile):
        console.print(f'Removed "{key}" from profile "{profile}".')
    else:
        console.print(f'Key "{key}" not found in profile "{profile}".')


@app.command("edit")
def edit_config() -> None:
    """Open the config file in your editor."""
    path = cfg.config_path()
    if not path.exists():
        # Create a default config
        cfg.save_config(cfg.DEFAULTS)
        console.print(f"Created default config at {path}")

    editor = os.environ.get("EDITOR", "vi")
    subprocess.run([editor, str(path)])


@app.command("path")
def show_path() -> None:
    """Show the config file path."""
    console.print(str(cfg.config_path()))
