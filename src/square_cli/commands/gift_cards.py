"""Gift card commands: list, get, create, activity."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="Manage gift cards.")
console = Console()


def _format_gift_card(gc) -> dict:
    d = gc.model_dump() if hasattr(gc, "model_dump") else gc
    balance = d.get("balance_money") or {}
    return {
        "id": d.get("id", ""),
        "gan": d.get("gan", ""),
        "state": d.get("state", ""),
        "type": d.get("type", ""),
        "balance": format_money(balance.get("amount")),
        "balance_cents": balance.get("amount"),
        "created_at": d.get("created_at", ""),
    }


GC_COLUMNS = [
    ("id", "ID"),
    ("gan", "GAN"),
    ("state", "State"),
    ("type", "Type"),
    ("balance", "Balance"),
    ("created_at", "Created"),
]


@app.command("list")
def list_gift_cards(
    state: Annotated[Optional[str], typer.Option("--state", "-s", help="Filter: ACTIVE, DEACTIVATED, etc.")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all gift cards."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_cards = []
        kwargs = {"limit": min(limit, 100)}
        if state:
            kwargs["state"] = state.upper()
        for gc in client.gift_cards.list(**kwargs):
            all_cards.append(gc)
            if len(all_cards) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_gift_card(gc) for gc in all_cards]
    print_output(items, columns=GC_COLUMNS, fmt=format, title=f"Gift Cards ({len(items)})")


@app.command("get")
def get_gift_card(
    card_id: Annotated[str, typer.Argument(help="Gift card ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a gift card."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.gift_cards.get(id=card_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square gift-cards list" to see cards.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    gc = response.gift_card
    if format == "json":
        data = gc.model_dump() if hasattr(gc, "model_dump") else gc
        print_single(data, fmt="json")
    else:
        item = _format_gift_card(gc)
        print_single(item, title=f"Gift Card {item['gan'] or item['id']}")


@app.command("create")
def create_gift_card(
    amount: Annotated[float, typer.Option("--amount", "-a", help="Initial balance in dollars")],
    type: Annotated[str, typer.Option("--type", "-t", help="Card type: DIGITAL or PHYSICAL")] = "DIGITAL",
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a new gift card."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.gift_cards.create(
            idempotency_key=str(uuid.uuid4()),
            location_id=None,  # Will use default
            gift_card={"type": type.upper()},
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    gc = response.gift_card
    gc_id = gc.id if hasattr(gc, "id") else "?"
    console.print(f"[green]Created gift card:[/] {gc_id}")

    if format == "json":
        data = gc.model_dump() if hasattr(gc, "model_dump") else gc
        print_single(data, fmt="json")


@app.command("activity")
def gift_card_activity(
    card_id: Annotated[str, typer.Argument(help="Gift card ID")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 50,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """View transaction history for a gift card."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_activities = []
        for act in client.gift_cards.activities.list(gift_card_id=card_id, limit=min(limit, 100)):
            all_activities.append(act)
            if len(all_activities) >= limit:
                break
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = []
    for a in all_activities:
        d = a.model_dump() if hasattr(a, "model_dump") else a
        amount = (d.get("gift_card_balance_money") or {}).get("amount")
        items.append({
            "id": d.get("id", ""),
            "type": d.get("type", ""),
            "balance_after": format_money(amount) if amount is not None else "",
            "created_at": d.get("created_at", ""),
        })

    columns = [("id", "ID"), ("type", "Type"), ("balance_after", "Balance After"), ("created_at", "Created")]
    print_output(items, columns=columns, fmt=format, title=f"Gift Card Activity ({len(items)})")
