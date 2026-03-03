"""Catalog commands: list, get, search, create, update, delete."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from ..client import get_client
from ..errors import APIError, handle_api_result, exit_with_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="Manage catalog items, categories, taxes, discounts, and modifiers.")
console = Console()


def _format_catalog_item(obj: dict) -> dict:
    """Flatten a Square catalog object for display."""
    item_data = obj.get("item_data", {})
    variations = item_data.get("variations", [])

    # Get price from first variation
    price_cents = None
    sku = None
    variation_id = None
    if variations:
        var = variations[0]
        variation_id = var.get("id")
        var_data = var.get("item_variation_data", {})
        sku = var_data.get("sku")
        price_money = var_data.get("price_money", {})
        price_cents = price_money.get("amount")

    return {
        "id": obj.get("id", ""),
        "type": obj.get("type", ""),
        "name": item_data.get("name", obj.get("category_data", {}).get("name", "")),
        "description": item_data.get("description", ""),
        "sku": sku or "",
        "price": format_money(price_cents) if price_cents is not None else "",
        "price_cents": price_cents,
        "variation_id": variation_id or "",
        "category_id": item_data.get("category_id", ""),
        "visibility": item_data.get("visibility", ""),
        "updated_at": obj.get("updated_at", ""),
    }


CATALOG_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("sku", "SKU"),
    ("price", "Price"),
    ("type", "Type"),
    ("updated_at", "Updated"),
]


@app.command("list")
def list_catalog(
    type: Annotated[
        Optional[str],
        typer.Option("--type", "-t", help="Filter by type: ITEM, CATEGORY, MODIFIER, TAX, DISCOUNT, IMAGE"),
    ] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all catalog items."""
    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    types = type or "ITEM"
    cursor = None
    all_objects: list[dict] = []

    while True:
        result = client.catalog.list_catalog(types=types, cursor=cursor)
        body = handle_api_result(result)
        objects = body.get("objects", [])
        all_objects.extend(objects)
        cursor = body.get("cursor")
        if not cursor:
            break

    items = [_format_catalog_item(obj) for obj in all_objects]
    print_output(items, columns=CATALOG_COLUMNS, fmt=format, title=f"Catalog ({len(items)} items)")


@app.command("get")
def get_item(
    object_id: Annotated[str, typer.Argument(help="Catalog object ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single catalog item."""
    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    result = client.catalog.retrieve_catalog_object(object_id=object_id)
    body = handle_api_result(result)
    obj = body.get("object", {})

    if format == "json":
        print_single(obj, fmt="json")
    else:
        item = _format_catalog_item(obj)
        print_single(item, title=item.get("name", "Catalog Item"))


@app.command("search")
def search_catalog(
    query: Annotated[str, typer.Argument(help="Search text")],
    category: Annotated[Optional[str], typer.Option("--category", help="Filter by category name")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Search catalog items by text query."""
    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    search_body: dict = {
        "object_types": ["ITEM"],
        "query": {
            "text_query": {
                "keywords": [query],
            }
        },
        "limit": min(limit, 100),
    }

    result = client.catalog.search_catalog_objects(body=search_body)
    body = handle_api_result(result)
    objects = body.get("objects", [])

    items = [_format_catalog_item(obj) for obj in objects]
    print_output(
        items,
        columns=CATALOG_COLUMNS,
        fmt=format,
        title=f'Search: "{query}" ({len(items)} results)',
    )


@app.command("create")
def create_item(
    name: Annotated[str, typer.Option("--name", help="Item name")],
    price: Annotated[Optional[float], typer.Option("--price", help="Price in dollars")] = None,
    sku: Annotated[Optional[str], typer.Option("--sku", help="SKU code")] = None,
    description: Annotated[Optional[str], typer.Option("--description", help="Item description")] = None,
    type: Annotated[str, typer.Option("--type", "-t", help="Object type: ITEM or CATEGORY")] = "ITEM",
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a new catalog item."""
    import uuid

    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    idempotency_key = str(uuid.uuid4())

    if type.upper() == "CATEGORY":
        body = {
            "idempotency_key": idempotency_key,
            "object": {
                "type": "CATEGORY",
                "id": f"#new_category_{idempotency_key[:8]}",
                "category_data": {"name": name},
            },
        }
    else:
        variation_data: dict = {
            "name": "Regular",
            "pricing_type": "FIXED_PRICING",
        }
        if price is not None:
            variation_data["price_money"] = {
                "amount": int(price * 100),
                "currency": "USD",
            }
        if sku:
            variation_data["sku"] = sku

        item_data: dict = {"name": name}
        if description:
            item_data["description"] = description

        body = {
            "idempotency_key": idempotency_key,
            "object": {
                "type": "ITEM",
                "id": f"#new_item_{idempotency_key[:8]}",
                "item_data": {
                    **item_data,
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": f"#new_var_{idempotency_key[:8]}",
                            "item_variation_data": variation_data,
                        }
                    ],
                },
            },
        }

    result = client.catalog.upsert_catalog_object(body=body)
    resp = handle_api_result(result)
    obj = resp.get("catalog_object", {})

    console.print(f'[green]Created:[/] {name} (ID: {obj.get("id", "?")})')
    if format == "json":
        print_single(obj, fmt="json")


@app.command("update")
def update_item(
    object_id: Annotated[str, typer.Argument(help="Catalog object ID to update")],
    name: Annotated[Optional[str], typer.Option("--name", help="New name")] = None,
    price: Annotated[Optional[float], typer.Option("--price", help="New price in dollars")] = None,
    description: Annotated[Optional[str], typer.Option("--description", help="New description")] = None,
    sku: Annotated[Optional[str], typer.Option("--sku", help="New SKU")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show changes without applying")] = False,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Update a catalog item's name, price, description, or SKU."""
    if not any([name, price is not None, description, sku]):
        exit_with_error("No changes specified.", hint="Use --name, --price, --description, or --sku.")

    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    # Fetch current object
    result = client.catalog.retrieve_catalog_object(object_id=object_id)
    body = handle_api_result(result)
    obj = body["object"]
    current = _format_catalog_item(obj)

    changes: list[str] = []
    item_data = obj.get("item_data", {})
    variations = item_data.get("variations", [])

    if name and name != item_data.get("name"):
        changes.append(f'  Name: "{item_data.get("name")}" -> "{name}"')
        item_data["name"] = name

    if description is not None and description != item_data.get("description", ""):
        old_desc = item_data.get("description", "(none)")
        changes.append(f'  Description: "{old_desc}" -> "{description}"')
        item_data["description"] = description

    if variations:
        var_data = variations[0].get("item_variation_data", {})
        if price is not None:
            old_price = var_data.get("price_money", {}).get("amount")
            new_price_cents = int(price * 100)
            if old_price != new_price_cents:
                changes.append(f"  Price: {format_money(old_price)} -> {format_money(new_price_cents)}")
                var_data["price_money"] = {"amount": new_price_cents, "currency": "USD"}

        if sku is not None and sku != var_data.get("sku", ""):
            changes.append(f'  SKU: "{var_data.get("sku", "")}" -> "{sku}"')
            var_data["sku"] = sku

    if not changes:
        console.print("[dim]No changes detected.[/]")
        return

    console.print(f'\n[bold]Changes for "{current["name"]}":[/]')
    for c in changes:
        console.print(c)

    if dry_run:
        console.print("\n[yellow]Dry run — no changes applied.[/]")
        return

    import uuid

    result = client.catalog.upsert_catalog_object(
        body={
            "idempotency_key": str(uuid.uuid4()),
            "object": obj,
        }
    )
    handle_api_result(result)
    console.print("\n[green]Updated successfully.[/]")


@app.command("delete")
def delete_item(
    object_id: Annotated[str, typer.Argument(help="Catalog object ID to delete")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompt")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Delete a catalog item."""
    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    # Fetch the item name for confirmation
    result = client.catalog.retrieve_catalog_object(object_id=object_id)
    body = handle_api_result(result)
    obj = body["object"]
    item = _format_catalog_item(obj)
    name = item.get("name", object_id)

    if not confirm:
        confirmed = typer.confirm(f'Delete "{name}" ({object_id})?')
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    result = client.catalog.delete_catalog_object(object_id=object_id)
    handle_api_result(result)
    console.print(f'[green]Deleted:[/] {name} ({object_id})')


@app.command("export")
def export_catalog(
    output: Annotated[str, typer.Option("--output", "-o", help="Output file path")] = "catalog.json",
    format: Annotated[str, typer.Option("--format", "-f", help="Export format: json or csv")] = "json",
    type: Annotated[str, typer.Option("--type", "-t", help="Object type to export")] = "ITEM",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Export the full catalog to a file."""
    import json as json_module
    from pathlib import Path

    client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

    cursor = None
    all_objects: list[dict] = []
    console.print(f"Fetching catalog ({type})...", end=" ")

    while True:
        result = client.catalog.list_catalog(types=type, cursor=cursor)
        body = handle_api_result(result)
        objects = body.get("objects", [])
        all_objects.extend(objects)
        cursor = body.get("cursor")
        if not cursor:
            break

    console.print(f"[green]{len(all_objects)} objects.[/]")

    path = Path(output)
    if format == "csv":
        import csv

        items = [_format_catalog_item(obj) for obj in all_objects]
        with open(path, "w", newline="") as f:
            if items:
                writer = csv.DictWriter(f, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)
    else:
        with open(path, "w") as f:
            json_module.dump(all_objects, f, indent=2, default=str)

    size = path.stat().st_size
    console.print(f"Saved to {path} ({size / 1024:.1f} KB)")
