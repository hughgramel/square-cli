"""Labor commands: shifts, timecards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="View shifts and timecards.")
console = Console()


# --- Shifts ---

shifts_app = typer.Typer(help="View team shifts.")
app.add_typer(shifts_app, name="shifts")


def _format_shift(s) -> dict:
    d = s.model_dump() if hasattr(s, "model_dump") else s
    return {
        "id": d.get("id", ""),
        "team_member_id": d.get("team_member_id", d.get("employee_id", "")),
        "start": d.get("start_at", ""),
        "end": d.get("end_at", ""),
        "status": d.get("status", ""),
        "location_id": d.get("location_id", ""),
    }


SHIFT_COLUMNS = [
    ("id", "ID"),
    ("team_member_id", "Member"),
    ("start", "Start"),
    ("end", "End"),
    ("status", "Status"),
]


@shifts_app.command("list")
def list_shifts(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 7,
    member_id: Annotated[Optional[str], typer.Option("--member", "-m", help="Team member ID")] = None,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List recent shifts."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    now = datetime.now(timezone.utc)
    start_at = (now - timedelta(days=days or 7)).isoformat()

    query: dict = {
        "filter": {
            "location_ids": [loc_id],
            "start": {"start_at": start_at},
        }
    }
    if member_id:
        query["filter"]["team_member_ids"] = [member_id]

    try:
        response = client.labor.shifts.search(query=query, limit=min(limit, 200))
    except ApiError as e:
        exit_with_error(format_api_error(e))

    shifts = response.shifts or []
    items = [_format_shift(s) for s in shifts]
    print_output(items, columns=SHIFT_COLUMNS, fmt=format, title=f"Shifts ({len(items)})")


# --- Timecards ---

timecards_app = typer.Typer(help="View timecards for payroll.")
app.add_typer(timecards_app, name="timecards")


def _format_timecard(tc) -> dict:
    d = tc.model_dump() if hasattr(tc, "model_dump") else tc
    return {
        "id": d.get("id", ""),
        "team_member_id": d.get("team_member_id", d.get("employee_id", "")),
        "clock_in": d.get("clock_in_at", ""),
        "clock_out": d.get("clock_out_at", ""),
        "status": d.get("status", ""),
        "location_id": d.get("location_id", ""),
    }


TIMECARD_COLUMNS = [
    ("id", "ID"),
    ("team_member_id", "Member"),
    ("clock_in", "Clock In"),
    ("clock_out", "Clock Out"),
    ("status", "Status"),
]


@timecards_app.command("list")
def list_timecards(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 14,
    member_id: Annotated[Optional[str], typer.Option("--member", "-m", help="Team member ID")] = None,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List recent timecards."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    now = datetime.now(timezone.utc)
    start_at = (now - timedelta(days=days or 14)).isoformat()

    query: dict = {
        "filter": {
            "location_ids": [loc_id],
            "clocked_in_at": {"start_at": start_at},
        }
    }
    if member_id:
        query["filter"]["team_member_ids"] = [member_id]

    try:
        response = client.labor.search_timecards(query=query, limit=min(limit, 200))
    except ApiError as e:
        exit_with_error(format_api_error(e))

    timecards = response.timecards or []
    items = [_format_timecard(tc) for tc in timecards]
    print_output(items, columns=TIMECARD_COLUMNS, fmt=format, title=f"Timecards ({len(items)})")
