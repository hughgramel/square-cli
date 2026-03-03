"""Inventory commands: list, get, adjust, set, history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage inventory and stock levels.")
console = Console()


def _format_count(count) -> dict:
    """Flatten an inventory count for display."""
    d = count.model_dump() if hasattr(count, "model_dump") else count
    return {
        "catalog_object_id": d.get("catalog_object_id", ""),
        "state": d.get("state", ""),
        "quantity": d.get("quantity", "0"),
        "location_id": d.get("location_id", ""),
        "calculated_at": d.get("calculated_at", ""),
    }


COUNT_COLUMNS = [
    ("catalog_object_id", "Catalog Object ID"),
    ("state", "State"),
    ("quantity", "Quantity"),
    ("location_id", "Location"),
    ("calculated_at", "As Of"),
]


@app.command("get")
def get_inventory(
    catalog_object_id: Annotated[str, typer.Argument(help="Catalog object ID (variation ID)")],
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get current stock for a catalog item (use variation ID)."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        response = client.inventory.batch_get_counts(
            catalog_object_ids=[catalog_object_id],
            location_ids=[loc_id],
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    counts = response.counts or []
    if not counts:
        console.print(f"[dim]No inventory data for {catalog_object_id}.[/]")
        return

    items = [_format_count(c) for c in counts]
    if format == "json":
        print_output(items, fmt="json")
    else:
        print_output(items, columns=COUNT_COLUMNS, fmt=format, title=f"Inventory: {catalog_object_id}")


@app.command("list")
def list_inventory(
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    low_stock: Annotated[Optional[int], typer.Option("--low-stock", help="Show items with stock below N")] = None,
    out_of_stock: Annotated[bool, typer.Option("--out-of-stock", help="Show only items with 0 stock")] = False,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List inventory counts. Use --low-stock or --out-of-stock to filter."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    # Get all catalog item variations first
    try:
        variation_ids = []
        for obj in client.catalog.list(types="ITEM"):
            d = obj.model_dump() if hasattr(obj, "model_dump") else obj
            for var in (d.get("item_data") or {}).get("variations") or []:
                variation_ids.append(var.get("id"))
    except ApiError as e:
        exit_with_error(format_api_error(e))

    if not variation_ids:
        console.print("[dim]No catalog items found.[/]")
        return

    # Batch get counts (max 100 per request)
    all_counts = []
    try:
        for i in range(0, len(variation_ids), 100):
            batch = variation_ids[i:i + 100]
            response = client.inventory.batch_get_counts(
                catalog_object_ids=batch,
                location_ids=[loc_id],
            )
            all_counts.extend(response.counts or [])
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_count(c) for c in all_counts]

    # Filter
    if out_of_stock:
        items = [i for i in items if _parse_qty(i["quantity"]) == 0]
    elif low_stock is not None:
        items = [i for i in items if _parse_qty(i["quantity"]) < low_stock]

    print_output(items, columns=COUNT_COLUMNS, fmt=format, title=f"Inventory ({len(items)} items)")


@app.command("adjust")
def adjust_inventory(
    catalog_object_id: Annotated[str, typer.Argument(help="Catalog variation ID")],
    delta: Annotated[int, typer.Option("--delta", help="Quantity change (+/-)")],
    reason: Annotated[Optional[str], typer.Option("--reason", "-r", help="Reason for adjustment")] = None,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Adjust inventory by a relative amount (positive or negative)."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    occurred_at = datetime.now(timezone.utc).isoformat()

    from_state = "IN_STOCK" if delta < 0 else "NONE"
    to_state = "NONE" if delta < 0 else "IN_STOCK"

    change = {
        "type": "ADJUSTMENT",
        "adjustment": {
            "catalog_object_id": catalog_object_id,
            "location_id": loc_id,
            "from_state": from_state,
            "to_state": to_state,
            "quantity": str(abs(delta)),
            "occurred_at": occurred_at,
        },
    }

    try:
        response = client.inventory.batch_create_changes(
            idempotency_key=str(uuid.uuid4()),
            changes=[change],
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    direction = "+" if delta > 0 else ""
    console.print(f"[green]Adjusted:[/] {catalog_object_id} {direction}{delta}")
    if reason:
        console.print(f"  Reason: {reason}")


@app.command("set")
def set_inventory(
    catalog_object_id: Annotated[str, typer.Argument(help="Catalog variation ID")],
    count: Annotated[int, typer.Option("--count", "-c", help="Absolute stock count")],
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Set inventory to an absolute count."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    occurred_at = datetime.now(timezone.utc).isoformat()

    change = {
        "type": "PHYSICAL_COUNT",
        "physical_count": {
            "catalog_object_id": catalog_object_id,
            "location_id": loc_id,
            "state": "IN_STOCK",
            "quantity": str(count),
            "occurred_at": occurred_at,
        },
    }

    try:
        response = client.inventory.batch_create_changes(
            idempotency_key=str(uuid.uuid4()),
            changes=[change],
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Set:[/] {catalog_object_id} → {count} units")


@app.command("history")
def inventory_history(
    catalog_object_id: Annotated[str, typer.Argument(help="Catalog variation ID")],
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """View inventory change history for an item."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        response = client.inventory.batch_get_changes(
            catalog_object_ids=[catalog_object_id],
            location_ids=[loc_id],
            limit=min(limit, 100),
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    changes = response.changes or []
    items = []
    for c in changes:
        d = c.model_dump() if hasattr(c, "model_dump") else c
        adj = d.get("adjustment") or d.get("physical_count") or {}
        items.append({
            "type": d.get("type", ""),
            "quantity": adj.get("quantity", ""),
            "from_state": adj.get("from_state", ""),
            "to_state": adj.get("to_state", adj.get("state", "")),
            "occurred_at": adj.get("occurred_at", ""),
        })

    columns = [
        ("type", "Type"),
        ("quantity", "Quantity"),
        ("from_state", "From"),
        ("to_state", "To"),
        ("occurred_at", "Occurred At"),
    ]
    print_output(items, columns=columns, fmt=format, title=f"Inventory History: {catalog_object_id}")


def _parse_qty(qty_str: str) -> int:
    """Parse a quantity string to int."""
    try:
        return int(float(qty_str))
    except (ValueError, TypeError):
        return 0
