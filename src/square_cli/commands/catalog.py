"""Catalog commands: list, get, search, create, update, delete."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error, print_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="Manage catalog items, categories, taxes, discounts, and modifiers.")
console = Console()


def _format_catalog_object(obj) -> dict:
    """Flatten a Square CatalogObject for display."""
    d = obj.model_dump() if hasattr(obj, "model_dump") else obj
    obj_type = d.get("type", "")
    item_data = d.get("item_data") or {}
    category_data = d.get("category_data") or {}
    variations = item_data.get("variations") or []

    price_cents = None
    sku = None
    variation_id = None
    if variations:
        var = variations[0]
        variation_id = var.get("id")
        var_data = var.get("item_variation_data") or {}
        sku = var_data.get("sku")
        price_money = var_data.get("price_money") or {}
        price_cents = price_money.get("amount")

    name = item_data.get("name") or category_data.get("name") or ""

    return {
        "id": d.get("id", ""),
        "type": obj_type,
        "name": name,
        "description": item_data.get("description", ""),
        "sku": sku or "",
        "price": format_money(price_cents) if price_cents is not None else "",
        "price_cents": price_cents,
        "variation_id": variation_id or "",
        "category_id": item_data.get("category_id", ""),
        "visibility": item_data.get("visibility", ""),
        "updated_at": d.get("updated_at", ""),
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
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    types = type or "ITEM"

    try:
        all_objects = []
        for page in client.catalog.list(types=types):
            all_objects.append(page)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_catalog_object(obj) for obj in all_objects]
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
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.catalog.object.get(object_id=object_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square catalog list" to see available items.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    obj = response.object
    if format == "json":
        data = obj.model_dump() if hasattr(obj, "model_dump") else obj
        print_single(data, fmt="json")
    else:
        item = _format_catalog_object(obj)
        print_single(item, title=item.get("name", "Catalog Item"))


@app.command("search")
def search_catalog(
    query: Annotated[str, typer.Argument(help="Search text")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Search catalog items by text query."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.catalog.search(
            object_types=["ITEM"],
            query={"text_query": {"keywords": [query]}},
            limit=min(limit, 100),
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    objects = response.objects or []
    items = [_format_catalog_object(obj) for obj in objects]
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

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    idempotency_key = str(uuid.uuid4())

    if type.upper() == "CATEGORY":
        obj_params = {
            "type": "CATEGORY",
            "id": f"#new_category_{idempotency_key[:8]}",
            "category_data": {"name": name},
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

        obj_params = {
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
        }

    try:
        response = client.catalog.object.upsert(
            idempotency_key=idempotency_key,
            object=obj_params,
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    created = response.catalog_object
    created_id = created.id if hasattr(created, "id") else "?"
    console.print(f"[green]Created:[/] {name} (ID: {created_id})")

    if format == "json":
        data = created.model_dump() if hasattr(created, "model_dump") else created
        print_single(data, fmt="json")


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

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.catalog.object.get(object_id=object_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square catalog list" to see available items.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    obj = response.object
    obj_dict = obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)
    current = _format_catalog_object(obj)

    changes: list[str] = []
    item_data = obj_dict.get("item_data") or {}
    variations = item_data.get("variations") or []

    if name and name != item_data.get("name"):
        changes.append(f'  Name: "{item_data.get("name")}" -> "{name}"')
        item_data["name"] = name

    if description is not None and description != item_data.get("description", ""):
        old_desc = item_data.get("description") or "(none)"
        changes.append(f'  Description: "{old_desc}" -> "{description}"')
        item_data["description"] = description

    if variations:
        var_data = variations[0].get("item_variation_data") or {}
        if price is not None:
            old_price = (var_data.get("price_money") or {}).get("amount")
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

    try:
        client.catalog.object.upsert(
            idempotency_key=str(uuid.uuid4()),
            object=obj_dict,
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

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
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.catalog.object.get(object_id=object_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square catalog list" to see available items.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    item = _format_catalog_object(response.object)
    item_name = item.get("name", object_id)

    if not confirm:
        confirmed = typer.confirm(f'Delete "{item_name}" ({object_id})?')
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.catalog.object.delete(object_id=object_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Deleted:[/] {item_name} ({object_id})")


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

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    all_objects = []
    console.print(f"Fetching catalog ({type})...", end=" ")

    try:
        for obj in client.catalog.list(types=type):
            all_objects.append(obj)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]{len(all_objects)} objects.[/]")

    path = Path(output)
    if format == "csv":
        import csv

        items = [_format_catalog_object(obj) for obj in all_objects]
        with open(path, "w", newline="") as f:
            if items:
                writer = csv.DictWriter(f, fieldnames=items[0].keys())
                writer.writeheader()
                writer.writerows(items)
    else:
        data = [
            obj.model_dump() if hasattr(obj, "model_dump") else obj
            for obj in all_objects
        ]
        with open(path, "w") as f:
            json_module.dump(data, f, indent=2, default=str)

    size = path.stat().st_size
    console.print(f"Saved to {path} ({size / 1024:.1f} KB)")
