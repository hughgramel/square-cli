"""Payment commands: list, get, refund."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="View payments and issue refunds.")
console = Console()


def _format_payment(pmt) -> dict:
    """Flatten a Square Payment for display."""
    d = pmt.model_dump() if hasattr(pmt, "model_dump") else pmt
    total_money = d.get("total_money") or d.get("amount_money") or {}
    tip_money = d.get("tip_money") or {}
    card = d.get("card_details") or {}
    card_info = card.get("card") or {}
    return {
        "id": d.get("id", ""),
        "status": d.get("status", ""),
        "amount": format_money(total_money.get("amount")),
        "amount_cents": total_money.get("amount"),
        "tip": format_money(tip_money.get("amount")) if tip_money.get("amount") else "",
        "card_brand": card_info.get("card_brand", ""),
        "last4": card_info.get("last_4", ""),
        "source_type": d.get("source_type", ""),
        "order_id": d.get("order_id", ""),
        "created_at": d.get("created_at", ""),
    }


PAYMENT_COLUMNS = [
    ("id", "ID"),
    ("status", "Status"),
    ("amount", "Amount"),
    ("tip", "Tip"),
    ("card_brand", "Card"),
    ("last4", "Last 4"),
    ("created_at", "Created"),
]


@app.command("list")
def list_payments(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 7,
    start: Annotated[Optional[str], typer.Option("--start", help="Start time (ISO)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="End time (ISO)")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: COMPLETED, PENDING, FAILED")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List recent payments."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    now = datetime.now(timezone.utc)
    if start and end:
        begin_time, end_time = start, end
    else:
        d = days or 7
        begin_time = (now - timedelta(days=d)).isoformat()
        end_time = now.isoformat()

    try:
        all_payments = []
        for pmt in client.payments.list(
            begin_time=begin_time,
            end_time=end_time,
            location_id=loc_id,
            limit=min(limit, 100),
        ):
            all_payments.append(pmt)
            if len(all_payments) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    if status:
        all_payments = [p for p in all_payments if (p.status if hasattr(p, "status") else (p.get("status") if isinstance(p, dict) else "")) == status.upper()]

    items = [_format_payment(p) for p in all_payments]
    print_output(items, columns=PAYMENT_COLUMNS, fmt=format, title=f"Payments ({len(items)})")


@app.command("get")
def get_payment(
    payment_id: Annotated[str, typer.Argument(help="Payment ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single payment."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.payments.get(payment_id=payment_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square payments list" to see recent payments.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    payment = response.payment
    if format == "json":
        data = payment.model_dump() if hasattr(payment, "model_dump") else payment
        print_single(data, fmt="json")
    else:
        item = _format_payment(payment)
        print_single(item, title=f"Payment {item['id']}")


@app.command("refund")
def refund_payment(
    payment_id: Annotated[str, typer.Argument(help="Payment ID to refund")],
    amount: Annotated[Optional[float], typer.Option("--amount", "-a", help="Refund amount in dollars")] = None,
    full: Annotated[bool, typer.Option("--full", help="Issue a full refund")] = False,
    reason: Annotated[Optional[str], typer.Option("--reason", "-r", help="Refund reason")] = None,
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompt")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Refund a payment (full or partial)."""
    import uuid

    if not amount and not full:
        exit_with_error("Specify --amount for partial refund or --full for full refund.")

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.payments.get(payment_id=payment_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square payments list" to see recent payments.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    payment = response.payment
    pmt_data = payment.model_dump() if hasattr(payment, "model_dump") else payment
    total_money = pmt_data.get("total_money") or pmt_data.get("amount_money") or {}
    total_cents = total_money.get("amount", 0)
    currency = total_money.get("currency", "USD")

    if full:
        refund_cents = total_cents
    else:
        refund_cents = int(amount * 100)

    if not confirm:
        confirmed = typer.confirm(
            f"Refund {format_money(refund_cents)} from payment {payment_id}?"
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        refund_params = {
            "idempotency_key": str(uuid.uuid4()),
            "payment_id": payment_id,
            "amount_money": {"amount": refund_cents, "currency": currency},
        }
        if reason:
            refund_params["reason"] = reason

        result = client.refunds.refund_payment(**refund_params)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    refund = result.refund
    refund_id = refund.id if hasattr(refund, "id") else "?"
    console.print(f"[green]Refund issued:[/] {format_money(refund_cents)} (Refund ID: {refund_id})")
