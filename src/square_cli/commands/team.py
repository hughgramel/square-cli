"""Team commands: list, get, create."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage team members.")
console = Console()


def _format_member(m) -> dict:
    """Flatten a Square TeamMember for display."""
    d = m.model_dump() if hasattr(m, "model_dump") else m
    return {
        "id": d.get("id", ""),
        "first_name": d.get("given_name", ""),
        "last_name": d.get("family_name", ""),
        "email": d.get("email_address", ""),
        "phone": d.get("phone_number", ""),
        "status": d.get("status", ""),
        "is_owner": d.get("is_owner", False),
        "created_at": d.get("created_at", ""),
    }


MEMBER_COLUMNS = [
    ("id", "ID"),
    ("first_name", "First"),
    ("last_name", "Last"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("status", "Status"),
]


@app.command("list")
def list_team(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: ACTIVE, INACTIVE")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all team members."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        query = {}
        if status:
            query["filter"] = {"status": {"members": [status.upper()]}}
        response = client.team_members.search(query=query, limit=min(limit, 200))
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    members = response.team_members or []
    items = [_format_member(m) for m in members]
    print_output(items, columns=MEMBER_COLUMNS, fmt=format, title=f"Team ({len(items)} members)")


@app.command("get")
def get_member(
    member_id: Annotated[str, typer.Argument(help="Team member ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a team member."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.team_members.get(team_member_id=member_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square team list" to see team members.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    member = response.team_member
    if format == "json":
        data = member.model_dump() if hasattr(member, "model_dump") else member
        print_single(data, fmt="json")
    else:
        item = _format_member(member)
        print_single(item, title=f"{item['first_name']} {item['last_name']}")


@app.command("create")
def create_member(
    first: Annotated[str, typer.Option("--first", help="First name")],
    last: Annotated[str, typer.Option("--last", help="Last name")],
    email: Annotated[Optional[str], typer.Option("--email", help="Email address")] = None,
    phone: Annotated[Optional[str], typer.Option("--phone", help="Phone number")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a new team member."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    params: dict = {
        "given_name": first,
        "family_name": last,
    }
    if email:
        params["email_address"] = email
    if phone:
        params["phone_number"] = phone

    try:
        response = client.team_members.create(team_member=params)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    member = response.team_member
    member_id = member.id if hasattr(member, "id") else "?"
    console.print(f"[green]Created:[/] {first} {last} (ID: {member_id})")

    if format == "json":
        data = member.model_dump() if hasattr(member, "model_dump") else member
        print_single(data, fmt="json")
