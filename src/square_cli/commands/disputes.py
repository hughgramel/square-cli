"""Dispute commands: list, get, accept."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="View and manage disputes (chargebacks).")
console = Console()


def _format_dispute(d_obj) -> dict:
    d = d_obj.model_dump() if hasattr(d_obj, "model_dump") else d_obj
    amount = d.get("amount_money") or {}
    return {
        "id": d.get("id", ""),
        "state": d.get("state", ""),
        "reason": d.get("reason", ""),
        "amount": format_money(amount.get("amount")),
        "card_brand": d.get("card_brand", ""),
        "due_at": d.get("due_at", ""),
        "created_at": d.get("created_at", ""),
    }


DISPUTE_COLUMNS = [
    ("id", "ID"),
    ("state", "State"),
    ("reason", "Reason"),
    ("amount", "Amount"),
    ("card_brand", "Card"),
    ("due_at", "Due"),
    ("created_at", "Created"),
]


@app.command("list")
def list_disputes(
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: INQUIRY_EVIDENCE_REQUIRED, INQUIRY_PROCESSING, etc.")] = None,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all disputes (chargebacks)."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_disputes = []
        kwargs = {}
        if status:
            kwargs["states"] = status.upper()
        if location_id:
            kwargs["location_id"] = location_id

        for dispute in client.disputes.list(**kwargs):
            all_disputes.append(dispute)
            if len(all_disputes) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_dispute(d) for d in all_disputes]
    print_output(items, columns=DISPUTE_COLUMNS, fmt=format, title=f"Disputes ({len(items)})")


@app.command("get")
def get_dispute(
    dispute_id: Annotated[str, typer.Argument(help="Dispute ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a dispute."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.disputes.get(dispute_id=dispute_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square disputes list" to see disputes.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    dispute = response.dispute
    if format == "json":
        data = dispute.model_dump() if hasattr(dispute, "model_dump") else dispute
        print_single(data, fmt="json")
    else:
        item = _format_dispute(dispute)
        print_single(item, title=f"Dispute {item['id']}")


@app.command("accept")
def accept_dispute(
    dispute_id: Annotated[str, typer.Argument(help="Dispute ID to accept")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Accept a dispute (concede the chargeback)."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Accept dispute {dispute_id}? This concedes the chargeback.")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.disputes.accept(dispute_id=dispute_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Dispute accepted:[/] {dispute_id}")
