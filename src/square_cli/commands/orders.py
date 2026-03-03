"""Order commands: list, get, search."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="View and search orders.")
console = Console()


def _format_order(order) -> dict:
    """Flatten a Square Order for display."""
    d = order.model_dump() if hasattr(order, "model_dump") else order
    total_money = d.get("total_money") or {}
    line_items = d.get("line_items") or []
    return {
        "id": d.get("id", ""),
        "state": d.get("state", ""),
        "total": format_money(total_money.get("amount")),
        "total_cents": total_money.get("amount"),
        "items": len(line_items),
        "source": (d.get("source") or {}).get("name", ""),
        "created_at": d.get("created_at", ""),
        "closed_at": d.get("closed_at", ""),
        "customer_id": d.get("customer_id", ""),
    }


ORDER_COLUMNS = [
    ("id", "ID"),
    ("state", "State"),
    ("total", "Total"),
    ("items", "Items"),
    ("source", "Source"),
    ("created_at", "Created"),
]


def _date_range(days: int | None, start: str | None, end: str | None):
    """Return (start_at, end_at) ISO strings."""
    if start and end:
        return start, end
    if days:
        now = datetime.now(timezone.utc)
        start_dt = now - timedelta(days=days)
        return start_dt.isoformat(), now.isoformat()
    # Default: last 7 days
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=7)).isoformat(), now.isoformat()


@app.command("list")
def list_orders(
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 7,
    start: Annotated[Optional[str], typer.Option("--start", help="Start date (ISO)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="End date (ISO)")] = None,
    status: Annotated[Optional[str], typer.Option("--status", "-s", help="Filter: OPEN, COMPLETED, CANCELED")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List recent orders."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    start_at, end_at = _date_range(days, start, end)

    date_filter = {
        "date_time_filter": {
            "created_at": {
                "start_at": start_at,
                "end_at": end_at,
            }
        }
    }

    if status:
        date_filter["state_filter"] = {"states": [status.upper()]}

    try:
        response = client.orders.search(
            location_ids=[loc_id],
            query=date_filter,
            limit=min(limit, 500),
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    orders = response.orders or []
    items = [_format_order(o) for o in orders]
    print_output(items, columns=ORDER_COLUMNS, fmt=format, title=f"Orders ({len(items)})")


@app.command("get")
def get_order(
    order_id: Annotated[str, typer.Argument(help="Order ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single order."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.orders.get(order_id=order_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square orders list" to see recent orders.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    order = response.order
    if format == "json":
        data = order.model_dump() if hasattr(order, "model_dump") else order
        print_single(data, fmt="json")
    else:
        item = _format_order(order)
        print_single(item, title=f"Order {item['id']}")

        # Print line items
        d = order.model_dump() if hasattr(order, "model_dump") else order
        line_items = d.get("line_items") or []
        if line_items:
            li_data = []
            for li in line_items:
                total = (li.get("total_money") or {}).get("amount")
                li_data.append({
                    "name": li.get("name", ""),
                    "quantity": li.get("quantity", ""),
                    "total": format_money(total),
                })
            print_output(
                li_data,
                columns=[("name", "Item"), ("quantity", "Qty"), ("total", "Total")],
                fmt="table",
                title="Line Items",
            )
