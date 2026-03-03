"""Invoice commands: list, get, create, send, cancel."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="Manage invoices.")
console = Console()


def _format_invoice(inv) -> dict:
    d = inv.model_dump() if hasattr(inv, "model_dump") else inv
    primary = (d.get("primary_recipient") or {})
    total = (d.get("computed_amount_money") or d.get("amount_money") or {})
    return {
        "id": d.get("id", ""),
        "invoice_number": d.get("invoice_number", ""),
        "status": d.get("status", ""),
        "title": d.get("title", ""),
        "amount": format_money(total.get("amount")),
        "customer_id": primary.get("customer_id", ""),
        "due_date": (d.get("payment_requests") or [{}])[0].get("due_date", "") if d.get("payment_requests") else "",
        "created_at": d.get("created_at", ""),
    }


INVOICE_COLUMNS = [
    ("id", "ID"),
    ("invoice_number", "Number"),
    ("status", "Status"),
    ("title", "Title"),
    ("amount", "Amount"),
    ("due_date", "Due Date"),
    ("created_at", "Created"),
]


@app.command("list")
def list_invoices(
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: DRAFT, UNPAID, PAID, etc.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List invoices."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_invoices = []
        for inv in client.invoices.list(location_id=loc_id, limit=min(limit, 100)):
            all_invoices.append(inv)
            if len(all_invoices) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    if status:
        all_invoices = [i for i in all_invoices if (i.status if hasattr(i, "status") else (i.get("status") if isinstance(i, dict) else "")) == status.upper()]

    items = [_format_invoice(i) for i in all_invoices]
    print_output(items, columns=INVOICE_COLUMNS, fmt=format, title=f"Invoices ({len(items)})")


@app.command("get")
def get_invoice(
    invoice_id: Annotated[str, typer.Argument(help="Invoice ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for an invoice."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.invoices.get(invoice_id=invoice_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square invoices list" to see invoices.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    invoice = response.invoice
    if format == "json":
        data = invoice.model_dump() if hasattr(invoice, "model_dump") else invoice
        print_single(data, fmt="json")
    else:
        item = _format_invoice(invoice)
        print_single(item, title=f"Invoice {item.get('invoice_number') or item['id']}")


@app.command("send")
def send_invoice(
    invoice_id: Annotated[str, typer.Argument(help="Invoice ID to send")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Publish and send an invoice to the customer."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        # Get current version
        response = client.invoices.get(invoice_id=invoice_id)
        invoice = response.invoice
        version = invoice.version if hasattr(invoice, "version") else 0
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Send invoice {invoice_id}?")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.invoices.publish(
            invoice_id=invoice_id,
            idempotency_key=str(uuid.uuid4()),
            version=version,
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Invoice sent:[/] {invoice_id}")


@app.command("cancel")
def cancel_invoice(
    invoice_id: Annotated[str, typer.Argument(help="Invoice ID to cancel")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Cancel an invoice."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.invoices.get(invoice_id=invoice_id)
        invoice = response.invoice
        version = invoice.version if hasattr(invoice, "version") else 0
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Cancel invoice {invoice_id}?")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.invoices.cancel(invoice_id=invoice_id, version=version)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Invoice cancelled:[/] {invoice_id}")
