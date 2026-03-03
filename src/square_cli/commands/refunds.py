"""Refund commands: list, get."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="View refunds.")
console = Console()


def _format_refund(ref) -> dict:
    """Flatten a Square Refund for display."""
    d = ref.model_dump() if hasattr(ref, "model_dump") else ref
    amount_money = d.get("amount_money") or {}
    return {
        "id": d.get("id", ""),
        "status": d.get("status", ""),
        "amount": format_money(amount_money.get("amount")),
        "amount_cents": amount_money.get("amount"),
        "payment_id": d.get("payment_id", ""),
        "reason": d.get("reason", ""),
        "created_at": d.get("created_at", ""),
    }


REFUND_COLUMNS = [
    ("id", "ID"),
    ("status", "Status"),
    ("amount", "Amount"),
    ("payment_id", "Payment ID"),
    ("reason", "Reason"),
    ("created_at", "Created"),
]


@app.command("list")
def list_refunds(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 30,
    start: Annotated[Optional[str], typer.Option("--start", help="Start time (ISO)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="End time (ISO)")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: PENDING, COMPLETED, REJECTED, FAILED")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List recent refunds."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    now = datetime.now(timezone.utc)
    if start and end:
        begin_time, end_time = start, end
    else:
        d = days or 30
        begin_time = (now - timedelta(days=d)).isoformat()
        end_time = now.isoformat()

    try:
        all_refunds = []
        for ref in client.refunds.list(
            begin_time=begin_time,
            end_time=end_time,
            location_id=loc_id,
            limit=min(limit, 100),
        ):
            all_refunds.append(ref)
            if len(all_refunds) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    if status:
        all_refunds = [r for r in all_refunds if (r.status if hasattr(r, "status") else (r.get("status") if isinstance(r, dict) else "")) == status.upper()]

    items = [_format_refund(r) for r in all_refunds]
    print_output(items, columns=REFUND_COLUMNS, fmt=format, title=f"Refunds ({len(items)})")


@app.command("get")
def get_refund(
    refund_id: Annotated[str, typer.Argument(help="Refund ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single refund."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.refunds.get(refund_id=refund_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square refunds list" to see recent refunds.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    refund = response.refund
    if format == "json":
        data = refund.model_dump() if hasattr(refund, "model_dump") else refund
        print_single(data, fmt="json")
    else:
        item = _format_refund(refund)
        print_single(item, title=f"Refund {item['id']}")
