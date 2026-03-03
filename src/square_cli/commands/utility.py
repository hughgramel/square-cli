"""Utility commands: version, resources, completion, feedback, docs."""

from __future__ import annotations

import webbrowser
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from .. import __version__

app = typer.Typer(help="Utility commands.")
console = Console()

SQUARE_DOCS_BASE = "https://developer.squareup.com/docs"
SQUARE_DOCS_MAP = {
    "catalog": f"{SQUARE_DOCS_BASE}/catalog-api/what-it-does",
    "orders": f"{SQUARE_DOCS_BASE}/orders-api/what-it-does",
    "payments": f"{SQUARE_DOCS_BASE}/payments-api/overview",
    "customers": f"{SQUARE_DOCS_BASE}/customers-api/what-it-does",
    "inventory": f"{SQUARE_DOCS_BASE}/inventory-api/what-it-does",
    "locations": f"{SQUARE_DOCS_BASE}/locations-api",
    "team": f"{SQUARE_DOCS_BASE}/team/overview",
    "labor": f"{SQUARE_DOCS_BASE}/labor-api/what-it-does",
    "loyalty": f"{SQUARE_DOCS_BASE}/loyalty-api/overview",
    "gift-cards": f"{SQUARE_DOCS_BASE}/gift-cards/using-gift-cards-api",
    "invoices": f"{SQUARE_DOCS_BASE}/invoices-api/overview",
    "subscriptions": f"{SQUARE_DOCS_BASE}/subscriptions-api/overview",
    "disputes": f"{SQUARE_DOCS_BASE}/disputes-api/overview",
    "webhooks": f"{SQUARE_DOCS_BASE}/webhooks/overview",
    "oauth": f"{SQUARE_DOCS_BASE}/oauth-api/overview",
    "terminal": f"{SQUARE_DOCS_BASE}/terminal-api/overview",
    "vendors": f"{SQUARE_DOCS_BASE}/vendors-api/manage-vendors-in-apps",
    "bookings": f"{SQUARE_DOCS_BASE}/bookings-api/what-it-is",
}

RESOURCES = [
    ("catalog", "Manage items, categories, taxes, discounts, modifiers, images"),
    ("orders", "View and manage orders"),
    ("sales", "Aggregated sales reports (by item, category, day, hour)"),
    ("payments", "View payments and process refunds"),
    ("refunds", "View refund history"),
    ("inventory", "Track stock levels, adjust counts, transfer between locations"),
    ("customers", "Manage customer profiles and groups"),
    ("locations", "View and manage business locations"),
    ("team", "Manage team members"),
    ("labor", "View shifts and timecards"),
    ("loyalty", "Manage loyalty program, accounts, and promotions"),
    ("gift-cards", "Manage gift cards and view activity"),
    ("invoices", "Create, send, and manage invoices"),
    ("disputes", "View and manage chargebacks"),
    ("subscriptions", "Manage recurring billing"),
    ("vendors", "Manage supplier/vendor records"),
    ("webhooks", "Manage webhook subscriptions"),
]


@app.command("version")
def version() -> None:
    """Show the CLI version."""
    console.print(f"square-cli {__version__}")


@app.command("resources")
def resources() -> None:
    """List all available API resources."""
    table = Table(title="Available Resources")
    table.add_column("Resource", style="bold")
    table.add_column("Description")

    for name, desc in RESOURCES:
        table.add_row(name, desc)

    console.print(table)
    console.print('\n[dim]Use "square <resource> --help" for resource-specific commands.[/]')


@app.command("docs")
def docs(
    resource: Annotated[Optional[str], typer.Argument(help="API resource to look up")] = None,
) -> None:
    """Open Square API documentation in your browser."""
    if resource and resource in SQUARE_DOCS_MAP:
        url = SQUARE_DOCS_MAP[resource]
        console.print(f"Opening docs for {resource}...")
    else:
        url = SQUARE_DOCS_BASE
        console.print("Opening Square API docs...")

    webbrowser.open(url)


@app.command("feedback")
def feedback() -> None:
    """Open the GitHub issues page to report bugs or request features."""
    url = "https://github.com/hughgramel/square-cli/issues"
    console.print("Opening GitHub issues...")
    webbrowser.open(url)
