"""Subscription commands: list, get, cancel, pause, resume."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output, print_single

app = typer.Typer(help="Manage subscriptions.")
console = Console()


def _format_subscription(sub) -> dict:
    d = sub.model_dump() if hasattr(sub, "model_dump") else sub
    price = d.get("price_override_money") or {}
    return {
        "id": d.get("id", ""),
        "customer_id": d.get("customer_id", ""),
        "plan_variation_id": d.get("plan_variation_id", ""),
        "status": d.get("status", ""),
        "price": format_money(price.get("amount")) if price.get("amount") else "",
        "start_date": d.get("start_date", ""),
        "charged_through_date": d.get("charged_through_date", ""),
        "created_at": d.get("created_at", ""),
    }


SUB_COLUMNS = [
    ("id", "ID"),
    ("customer_id", "Customer"),
    ("status", "Status"),
    ("price", "Price"),
    ("start_date", "Start"),
    ("charged_through_date", "Charged Through"),
]


@app.command("list")
def list_subscriptions(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all subscriptions."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.subscriptions.search(limit=min(limit, 200))
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    subs = response.subscriptions or []
    items = [_format_subscription(s) for s in subs]
    print_output(items, columns=SUB_COLUMNS, fmt=format, title=f"Subscriptions ({len(items)})")


@app.command("get")
def get_subscription(
    subscription_id: Annotated[str, typer.Argument(help="Subscription ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a subscription."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.subscriptions.get(subscription_id=subscription_id)
    except ApiError as e:
        exit_with_error(format_api_error(e), hint='Run "square subscriptions list" to see subscriptions.')
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    sub = response.subscription
    if format == "json":
        data = sub.model_dump() if hasattr(sub, "model_dump") else sub
        print_single(data, fmt="json")
    else:
        item = _format_subscription(sub)
        print_single(item, title=f"Subscription {item['id']}")


@app.command("cancel")
def cancel_subscription(
    subscription_id: Annotated[str, typer.Argument(help="Subscription ID to cancel")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Cancel a subscription."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Cancel subscription {subscription_id}?")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.subscriptions.cancel(subscription_id=subscription_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Subscription cancelled:[/] {subscription_id}")


@app.command("pause")
def pause_subscription(
    subscription_id: Annotated[str, typer.Argument(help="Subscription ID to pause")],
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Pause a subscription."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        client.subscriptions.pause(subscription_id=subscription_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    console.print(f"[green]Subscription paused:[/] {subscription_id}")


@app.command("resume")
def resume_subscription(
    subscription_id: Annotated[str, typer.Argument(help="Subscription ID to resume")],
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Resume a paused subscription."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        client.subscriptions.resume(subscription_id=subscription_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    console.print(f"[green]Subscription resumed:[/] {subscription_id}")
