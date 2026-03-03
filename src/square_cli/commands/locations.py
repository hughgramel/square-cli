"""Location commands: list, get, set-default."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..config import save_config
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage business locations.")
console = Console()


def _format_location(loc) -> dict:
    """Flatten a Square Location for display."""
    d = loc.model_dump() if hasattr(loc, "model_dump") else loc
    address = d.get("address") or {}
    return {
        "id": d.get("id", ""),
        "name": d.get("name", ""),
        "status": d.get("status", ""),
        "address": ", ".join(
            filter(None, [
                address.get("address_line_1"),
                address.get("locality"),
                address.get("administrative_district_level_1"),
                address.get("postal_code"),
            ])
        ),
        "phone": d.get("phone_number", ""),
        "timezone": d.get("timezone", ""),
        "country": d.get("country", ""),
        "type": d.get("type", ""),
        "created_at": d.get("created_at", ""),
    }


LOCATION_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("address", "Address"),
    ("phone", "Phone"),
    ("timezone", "Timezone"),
]


@app.command("list")
def list_locations(
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all business locations."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.locations.list()
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    locations = response.locations or []
    items = [_format_location(loc) for loc in locations]
    print_output(items, columns=LOCATION_COLUMNS, fmt=format, title=f"Locations ({len(items)})")


@app.command("get")
def get_location(
    location_id: Annotated[str, typer.Argument(help="Location ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single location."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.locations.get(location_id=location_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square locations list" to see available locations.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    loc = response.location
    if format == "json":
        data = loc.model_dump() if hasattr(loc, "model_dump") else loc
        print_single(data, fmt="json")
    else:
        item = _format_location(loc)
        print_single(item, title=item.get("name", "Location"))


@app.command("set-default")
def set_default(
    location_id: Annotated[str, typer.Argument(help="Location ID to set as default")],
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Set a default location for subsequent commands."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.locations.get(location_id=location_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square locations list" to see available locations.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    loc = response.location
    name = loc.name if hasattr(loc, "name") else location_id

    save_config({"location_id": location_id}, profile=profile)
    console.print(f'[green]Default location set:[/] {name} ({location_id})')
