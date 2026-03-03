"""Webhook commands: list, create, delete."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage webhook subscriptions.")
console = Console()


def _format_webhook(wh) -> dict:
    d = wh.model_dump() if hasattr(wh, "model_dump") else wh
    return {
        "id": d.get("id", ""),
        "name": d.get("name", ""),
        "enabled": d.get("enabled", False),
        "notification_url": d.get("notification_url", ""),
        "api_version": d.get("api_version", ""),
        "event_types": ", ".join(d.get("event_types") or []),
        "created_at": d.get("created_at", ""),
    }


WH_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("enabled", "Enabled"),
    ("notification_url", "URL"),
    ("event_types", "Events"),
]


@app.command("list")
def list_webhooks(
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List registered webhook subscriptions."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    try:
        all_subs = []
        for sub in client.webhooks.subscriptions.list():
            all_subs.append(sub)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    items = [_format_webhook(s) for s in all_subs]
    print_output(items, columns=WH_COLUMNS, fmt=format, title=f"Webhooks ({len(items)})")


@app.command("create")
def create_webhook(
    name: Annotated[str, typer.Option("--name", help="Subscription name")],
    url: Annotated[str, typer.Option("--url", help="Notification URL")],
    events: Annotated[str, typer.Option("--events", help="Comma-separated event types")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Create a webhook subscription."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    event_list = [e.strip() for e in events.split(",")]

    try:
        response = client.webhooks.subscriptions.create(
            idempotency_key=str(uuid.uuid4()),
            subscription={
                "name": name,
                "notification_url": url,
                "event_types": event_list,
                "enabled": True,
            },
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))

    sub = response.subscription
    sub_id = sub.id if hasattr(sub, "id") else "?"
    console.print(f"[green]Created webhook:[/] {name} (ID: {sub_id})")

    if format == "json":
        data = sub.model_dump() if hasattr(sub, "model_dump") else sub
        print_single(data, fmt="json")


@app.command("delete")
def delete_webhook(
    subscription_id: Annotated[str, typer.Argument(help="Webhook subscription ID to delete")],
    confirm: Annotated[bool, typer.Option("--confirm", help="Skip confirmation")] = False,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Delete a webhook subscription."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    if not confirm:
        confirmed = typer.confirm(f"Delete webhook subscription {subscription_id}?")
        if not confirmed:
            console.print("[dim]Cancelled.[/]")
            raise typer.Exit()

    try:
        client.webhooks.subscriptions.delete(subscription_id=subscription_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    console.print(f"[green]Deleted webhook:[/] {subscription_id}")


@app.command("event-types")
def list_event_types(
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all available webhook event types."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.webhooks.event_types.list()
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    event_types = response.event_types or []
    items = [{"event_type": et} for et in event_types]
    print_output(items, columns=[("event_type", "Event Type")], fmt=format, title=f"Event Types ({len(items)})")
