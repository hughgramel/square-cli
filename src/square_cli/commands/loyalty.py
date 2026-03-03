"""Loyalty commands: program, accounts, points."""

from __future__ import annotations

from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client
from ..errors import exit_with_error, format_api_error
from ..output import print_output, print_single

app = typer.Typer(help="Manage loyalty program and accounts.")
console = Console()


@app.command("program")
def show_program(
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """View your loyalty program configuration."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.loyalty.programs.get(program_id="main")
    except ApiError as e:
        exit_with_error(format_api_error(e), hint="Your account may not have a loyalty program set up.")
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    program = response.program
    data = program.model_dump() if hasattr(program, "model_dump") else program
    if format == "json":
        print_single(data, fmt="json")
    else:
        print_single({
            "id": data.get("id", ""),
            "status": data.get("status", ""),
            "terminology_one": (data.get("terminology") or {}).get("one", ""),
            "terminology_other": (data.get("terminology") or {}).get("other", ""),
            "created_at": data.get("created_at", ""),
            "updated_at": data.get("updated_at", ""),
        }, title="Loyalty Program")


# --- Accounts ---

accounts_app = typer.Typer(help="Manage loyalty accounts.")
app.add_typer(accounts_app, name="accounts")


def _format_account(acct) -> dict:
    d = acct.model_dump() if hasattr(acct, "model_dump") else acct
    return {
        "id": d.get("id", ""),
        "customer_id": d.get("customer_id", ""),
        "balance": d.get("balance", 0),
        "lifetime_points": d.get("lifetime_points", 0),
        "enrolled_at": d.get("enrolled_at", d.get("created_at", "")),
    }


ACCOUNT_COLUMNS = [
    ("id", "ID"),
    ("customer_id", "Customer ID"),
    ("balance", "Balance"),
    ("lifetime_points", "Lifetime Points"),
    ("enrolled_at", "Enrolled"),
]


@accounts_app.command("list")
def list_accounts(
    limit: Annotated[int, typer.Option("--limit", "-n", help="Max results")] = 100,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """List all loyalty accounts."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.loyalty.accounts.search(limit=min(limit, 200))
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    accounts = response.loyalty_accounts or []
    items = [_format_account(a) for a in accounts]
    print_output(items, columns=ACCOUNT_COLUMNS, fmt=format, title=f"Loyalty Accounts ({len(items)})")


@accounts_app.command("get")
def get_account(
    account_id: Annotated[str, typer.Argument(help="Loyalty account ID")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Get details for a loyalty account."""
    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        response = client.loyalty.accounts.get(account_id=account_id)
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    account = response.loyalty_account
    if format == "json":
        data = account.model_dump() if hasattr(account, "model_dump") else account
        print_single(data, fmt="json")
    else:
        item = _format_account(account)
        print_single(item, title=f"Loyalty Account {item['id']}")


@accounts_app.command("search")
def search_accounts(
    phone: Annotated[Optional[str], typer.Option("--phone", help="Search by phone number")] = None,
    customer_id: Annotated[Optional[str], typer.Option("--customer", help="Search by customer ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Search loyalty accounts by phone or customer ID."""
    if not phone and not customer_id:
        exit_with_error("Specify --phone or --customer to search.")

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        query: dict = {}
        if phone:
            query["mappings"] = [{"phone_number": phone}]
        if customer_id:
            query["customer_ids"] = [customer_id]

        response = client.loyalty.accounts.search(query=query)
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    accounts = response.loyalty_accounts or []
    items = [_format_account(a) for a in accounts]
    print_output(items, columns=ACCOUNT_COLUMNS, fmt=format, title=f"Loyalty Accounts ({len(items)})")


# --- Points ---

@app.command("points")
def add_points(
    account_id: Annotated[str, typer.Argument(help="Loyalty account ID")],
    points: Annotated[int, typer.Option("--points", help="Number of points to add")],
    reason: Annotated[Optional[str], typer.Option("--reason", "-r", help="Reason for adjustment")] = None,
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """Add loyalty points to an account."""
    import uuid

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)

        # Get the program ID
        program_response = client.loyalty.programs.get(program_id="main")
        program_id = program_response.program.id

        response = client.loyalty.accounts.adjust(
            account_id=account_id,
            idempotency_key=str(uuid.uuid4()),
            adjust_points={
                "loyalty_program_id": program_id,
                "points": points,
                "reason": reason or "CLI adjustment",
            },
        )
    except ApiError as e:
        exit_with_error(format_api_error(e))
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    console.print(f"[green]Added {points} points[/] to account {account_id}")
