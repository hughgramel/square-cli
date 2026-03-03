"""Square CLI — manage your Square business from the command line."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console

from . import __version__
from .commands import (
    auth_cmd, catalog, config_cmd, customers, disputes, gift_cards,
    http, inventory, invoices, labor, locations, loyalty, orders, payments,
    refunds, sales, subscriptions, team, utility, vendors, webhooks,
)
from .errors import AuthError, SquareCLIError, print_error

console = Console()

app = typer.Typer(
    name="square",
    help="A CLI for Square — manage catalog, sales, inventory, customers, and more.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


# --- Register command groups ---

# Auth (top-level: square login, square logout, square status)
app.command("login")(auth_cmd.login)
app.command("logout")(auth_cmd.logout)
app.command("status")(auth_cmd.status)

# Config
app.add_typer(config_cmd.app, name="config")

# Catalog
app.add_typer(catalog.app, name="catalog")

# Locations
app.add_typer(locations.app, name="locations")

# Orders
app.add_typer(orders.app, name="orders")

# Sales (top-level: square sales)
app.add_typer(sales.app, name="sales")

# Payments
app.add_typer(payments.app, name="payments")

# Refunds
app.add_typer(refunds.app, name="refunds")

# Inventory
app.add_typer(inventory.app, name="inventory")

# Customers
app.add_typer(customers.app, name="customers")

# Team
app.add_typer(team.app, name="team")

# Labor
app.add_typer(labor.app, name="labor")

# Loyalty
app.add_typer(loyalty.app, name="loyalty")

# Gift Cards
app.add_typer(gift_cards.app, name="gift-cards")

# Invoices
app.add_typer(invoices.app, name="invoices")

# Disputes
app.add_typer(disputes.app, name="disputes")

# Subscriptions
app.add_typer(subscriptions.app, name="subscriptions")

# Vendors
app.add_typer(vendors.app, name="vendors")

# Webhooks
app.add_typer(webhooks.app, name="webhooks")

# Raw HTTP (top-level: square get, square post, square delete)
app.command("get", help="Make a raw GET request to the Square API.")(http.http_get)
app.command("post", help="Make a raw POST request to the Square API.")(http.http_post)

# Utility (top-level: square version, square resources, etc.)
app.command("version")(utility.version)
app.command("resources")(utility.resources)
app.command("docs")(utility.docs)
app.command("feedback")(utility.feedback)


# --- Version callback ---

def _version_callback(value: bool) -> None:
    if value:
        console.print(f"square-cli {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Show version and exit.", callback=_version_callback, is_eager=True),
    ] = None,
) -> None:
    """Square CLI — manage your Square business from the command line."""
    pass
