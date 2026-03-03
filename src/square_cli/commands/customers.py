"""Customer commands: list, get, search, create, update, delete."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage customers.")
console = Console()


def _format_customer(cust) -> dict:
    """Flatten a Square Customer for display."""
    d = cust.model_dump() if hasattr(cust, "model_dump") else cust
    address = d.get("address") or {}
    return {
        "id": d.get("id", ""),
        "name": " ".join(filter(None, [d.get("given_name"), d.get("family_name")])),
        "email": d.get("email_address", ""),
        "phone": d.get("phone_number", ""),
        "company": d.get("company_name", ""),
        "city": address.get("locality", ""),
        "note": d.get("note", ""),
        "created_at": d.get("created_at", ""),
    }


CUSTOMER_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("company", "Company"),
    ("created_at", "Created"),
]


@app.command("list")
def list_customers(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    sort: Annotated[str, typer.Option("--sort", help="Sort: CREATED_AT, DEFAULT")] = "DEFAULT",
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all customers."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_customers = []
        for cust in client.customers.list(limit=min(limit, 100)):
            all_customers.append(cust)
            if len(all_customers) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_customer(c) for c in all_customers]
    print_output(items, columns=CUSTOMER_COLUMNS, fmt=format, title=f"Customers ({len(items)})")


@app.command("get")
def get_customer(
    customer_id: Annotated[str, typer.Argument(help="Customer ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a single customer."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.customers.get(customer_id=customer_id)
    except ApiError as e:
        exit_with_error(
            format_api_error(e),
            hint='Run "square customers list" to see available customers.',
        )
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    customer = response.customer
    if format == "json":
        data = customer.model_dump() if hasattr(customer, "model_dump") else customer
        print_single(data, fmt="json")
    else:
        item = _format_customer(customer)
        print_single(item, title=item.get("name", "Customer"))


@app.command("search")
def search_customers(
    query: Annotated[str, typer.Argument(help="Search text (name, email, or phone)")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Search customers by name, email, or phone."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.customers.search(
            query={
                "filter": {
                    "email_address": {"fuzzy": query},
                },
            },
            limit=min(limit, 100),
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    customers = response.customers or []
    items = [_format_customer(c) for c in customers]
    print_output(
        items,
        columns=CUSTOMER_COLUMNS,
        fmt=format,
        title=f'Search: "{query}" ({len(items)} results)',
    )


@app.command("create")
def create_customer(
    name: Annotated[Optional[str], typer.Option("--name", help="Full name (or use --first/--last)")] = None,
    first: Annotated[Optional[str], typer.Option("--first", help="First name")] = None,
    last: Annotated[Optional[str], typer.Option("--last", help="Last name")] = None,
    email: Annotated[Optional[str], typer.Option("--email", help="Email address")] = None,
    phone: Annotated[Optional[str], typer.Option("--phone", help="Phone number")] = None,
    company: Annotated[Optional[str], typer.Option("--company", help="Company name")] = None,
    note: Annotated[Optional[str], typer.Option("--note", help="Customer note")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a new customer."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    params: dict = {}
    if name:
        parts = name.split(None, 1)
        params["given_name"] = parts[0]
        if len(parts) > 1:
            params["family_name"] = parts[1]
    if first:
        params["given_name"] = first
    if last:
        params["family_name"] = last
    if email:
        params["email_address"] = email
    if phone:
        params["phone_number"] = phone
    if company:
        params["company_name"] = company
    if note:
        params["note"] = note

    if not params:
        exit_with_error("No customer data provided.", hint="Use --name, --email, --phone, etc.")

    try:
        response = client.customers.create(**params)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    customer = response.customer
    cust_id = customer.id if hasattr(customer, "id") else "?"
    display_name = " ".join(filter(None, [
        getattr(customer, "given_name", ""),
        getattr(customer, "family_name", ""),
    ])) or cust_id
    console.print(f"[green]Created:[/] {display_name} (ID: {cust_id})")

    if format == "json":
        data = customer.model_dump() if hasattr(customer, "model_dump") else customer
        print_single(data, fmt="json")


@app.command("update")
def update_customer(
    customer_id: Annotated[str, typer.Argument(help="Customer ID to update")],
    name: Annotated[Optional[str], typer.Option("--name", help="New full name")] = None,
    email: Annotated[Optional[str], typer.Option("--email", help="New email")] = None,
    phone: Annotated[Optional[str], typer.Option("--phone", help="New phone")] = None,
    company: Annotated[Optional[str], typer.Option("--company", help="New company name")] = None,
    note: Annotated[Optional[str], typer.Option("--note", help="New note")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Update a customer's details."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    params: dict = {}
    if name:
        parts = name.split(None, 1)
        params["given_name"] = parts[0]
        if len(parts) > 1:
            params["family_name"] = parts[1]
    if email:
        params["email_address"] = email
    if phone:
        params["phone_number"] = phone
    if company:
        params["company_name"] = company
    if note:
        params["note"] = note

    if not params:
        exit_with_error("No changes specified.", hint="Use --name, --email, --phone, --company, or --note.")

    try:
        response = client.customers.update(customer_id=customer_id, **params)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square customers list" to see customers.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    console.print(f"[green]Updated:[/] {customer_id}")


@app.command("delete")
def delete_customer(
    customer_id: Annotated[str, typer.Argument(help="Customer ID to delete")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation prompt")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Delete a customer."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Delete customer {customer_id}?")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.customers.delete(customer_id=customer_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Deleted:[/] {customer_id}")
