"""Vendor commands: list, get, create, search, update."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage vendors (suppliers).")
console = Console()


def _format_vendor(v) -> dict:
    d = v.model_dump() if hasattr(v, "model_dump") else v
    contacts = d.get("contacts") or []
    primary = contacts[0] if contacts else {}
    return {
        "id": d.get("id", ""),
        "name": d.get("name", ""),
        "status": d.get("status", ""),
        "contact_name": primary.get("name", ""),
        "contact_email": primary.get("email_address", ""),
        "contact_phone": primary.get("phone_number", ""),
        "note": d.get("note", ""),
        "created_at": d.get("created_at", ""),
    }


VENDOR_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("contact_name", "Contact"),
    ("contact_email", "Email"),
    ("note", "Note"),
]


@app.command("list")
def list_vendors(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all vendors."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.vendors.search(limit=min(limit, 100))
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    vendors = response.vendors or []
    items = [_format_vendor(v) for v in vendors]
    print_output(items, columns=VENDOR_COLUMNS, fmt=format, title=f"Vendors ({len(items)})")


@app.command("get")
def get_vendor(
    vendor_id: Annotated[str, typer.Argument(help="Vendor ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a vendor."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.vendors.get(vendor_id=vendor_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square vendors list" to see vendors.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    vendor = response.vendor
    if format == "json":
        data = vendor.model_dump() if hasattr(vendor, "model_dump") else vendor
        print_single(data, fmt="json")
    else:
        item = _format_vendor(vendor)
        print_single(item, title=item.get("name", "Vendor"))


@app.command("create")
def create_vendor(
    name: Annotated[str, typer.Option("--name", help="Vendor name")],
    note: Annotated[Optional[str], typer.Option("--note", help="Vendor note")] = None,
    contact_name: Annotated[Optional[str], typer.Option("--contact-name", help="Contact name")] = None,
    contact_email: Annotated[Optional[str], typer.Option("--contact-email", help="Contact email")] = None,
    contact_phone: Annotated[Optional[str], typer.Option("--contact-phone", help="Contact phone")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a new vendor."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    vendor_data: dict = {"name": name}
    if note:
        vendor_data["note"] = note

    contacts = []
    if any([contact_name, contact_email, contact_phone]):
        contact: dict = {}
        if contact_name:
            contact["name"] = contact_name
        if contact_email:
            contact["email_address"] = contact_email
        if contact_phone:
            contact["phone_number"] = contact_phone
        contacts.append(contact)
    if contacts:
        vendor_data["contacts"] = contacts

    try:
        response = client.vendors.create(
            idempotency_key=str(uuid.uuid4()),
            vendor=vendor_data,
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    vendor = response.vendor
    vendor_id = vendor.id if hasattr(vendor, "id") else "?"
    console.print(f"[green]Created:[/] {name} (ID: {vendor_id})")

    if format == "json":
        data = vendor.model_dump() if hasattr(vendor, "model_dump") else vendor
        print_single(data, fmt="json")


@app.command("search")
def search_vendors(
    query: Annotated[str, typer.Argument(help="Search text")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Search vendors by name."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.vendors.search(
            filter={"name": [query]},
            limit=min(limit, 100),
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    vendors = response.vendors or []
    items = [_format_vendor(v) for v in vendors]
    print_output(
        items,
        columns=VENDOR_COLUMNS,
        fmt=format,
        title=f'Search: "{query}" ({len(items)} results)',
    )


@app.command("update")
def update_vendor(
    vendor_id: Annotated[str, typer.Argument(help="Vendor ID to update")],
    name: Annotated[Optional[str], typer.Option("--name", help="New name")] = None,
    note: Annotated[Optional[str], typer.Option("--note", help="New note")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Update a vendor."""
    if not any([name, note]):
        exit_with_error("No changes specified.", hint="Use --name or --note.")

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    vendor_data: dict = {}
    if name:
        vendor_data["name"] = name
    if note is not None:
        vendor_data["note"] = note

    try:
        client.vendors.update(vendor_id=vendor_id, vendor=vendor_data)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Updated:[/] {vendor_id}")
