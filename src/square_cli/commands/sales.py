"""Sales commands: aggregated sales reporting."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer
from rich.console import Console
from square.core.api_error import ApiError

from ..client import get_client, get_location_id
from ..errors import exit_with_error, format_api_error
from ..output import format_money, print_output

app = typer.Typer(help="Sales reports and analytics.")
console = Console()


def _fetch_completed_orders(client, location_id: str, start_at: str, end_at: str) -> list[dict]:
    """Fetch all completed orders in a date range."""
    all_orders = []
    cursor = None
    seen_cursors: set[str] = set()

    while True:
        body: dict = {
            "location_ids": [location_id],
            "query": {
                "filter": {
                    "date_time_filter": {
                        "closed_at": {
                            "start_at": start_at,
                            "end_at": end_at,
                        }
                    },
                    "state_filter": {"states": ["COMPLETED"]},
                },
                "sort": {
                    "sort_field": "CLOSED_AT",
                    "sort_order": "DESC",
                },
            },
            "limit": 500,
        }
        if cursor:
            body["cursor"] = cursor

        response = client.orders.search(**body)
        orders = response.orders or []
        for o in orders:
            d = o.model_dump() if hasattr(o, "model_dump") else o
            all_orders.append(d)

        cursor = getattr(response, "cursor", None) or None
        if not cursor or not orders:
            break
        # Safety: detect repeated cursors to prevent infinite loops
        if cursor in seen_cursors:
            break
        seen_cursors.add(cursor)

    return all_orders


def _date_range(days: int | None, start: str | None, end: str | None):
    now = datetime.now(timezone.utc)
    if start and end:
        return start, end
    d = days or 7
    return (now - timedelta(days=d)).isoformat(), now.isoformat()


@app.callback(invoke_without_command=True)
def sales_summary(
    ctx: typer.Context,
    days: Annotated[Optional[int], typer.Option("--days", "-d", help="Number of past days")] = 7,
    start: Annotated[Optional[str], typer.Option("--start", help="Start date (ISO)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", help="End date (ISO)")] = None,
    by_item: Annotated[bool, typer.Option("--by-item", help="Breakdown by catalog item")] = False,
    by_category: Annotated[bool, typer.Option("--by-category", help="Breakdown by category")] = False,
    by_day: Annotated[bool, typer.Option("--by-day", help="Daily revenue trend")] = False,
    by_hour: Annotated[bool, typer.Option("--by-hour", help="Hourly breakdown")] = False,
    by_payment_method: Annotated[bool, typer.Option("--by-payment-method", help="Breakdown by payment method")] = False,
    top: Annotated[Optional[int], typer.Option("--top", help="Show top N items by revenue")] = None,
    bottom: Annotated[Optional[int], typer.Option("--bottom", help="Show bottom N items by revenue")] = None,
    location_id: Annotated[Optional[str], typer.Option("--location", "-l", help="Location ID")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output: table, json, csv")] = "table",
    access_token: Annotated[Optional[str], typer.Option("--access-token", hidden=True)] = None,
    profile: Annotated[str, typer.Option("--profile", "-p", help="Profile")] = "default",
    sandbox: Annotated[bool, typer.Option("--sandbox", help="Use sandbox")] = False,
) -> None:
    """View sales reports. Defaults to a revenue summary for the past 7 days."""
    if ctx.invoked_subcommand is not None:
        return

    try:
        client = get_client(access_token=access_token, profile=profile, sandbox=sandbox)
        loc_id = get_location_id(client, location_id, profile)
    except Exception as e:
        exit_with_error(str(e), hint=getattr(e, "hint", None))

    start_at, end_at = _date_range(days, start, end)

    try:
        orders = _fetch_completed_orders(client, loc_id, start_at, end_at)
    except ApiError as e:
        exit_with_error(format_api_error(e))

    if not orders:
        console.print("[dim]No completed orders found for this period.[/]")
        return

    if by_item:
        _report_by_item(orders, format, top, bottom)
    elif by_day:
        _report_by_day(orders, format)
    elif by_hour:
        _report_by_hour(orders, format)
    elif by_payment_method:
        _report_by_payment_method(orders, format)
    elif by_category:
        _report_by_category(orders, format)
    else:
        _report_summary(orders, format, days or 7)


def _report_summary(orders: list[dict], fmt: str, days: int) -> None:
    """Overall revenue summary."""
    total_cents = 0
    total_items = 0
    for o in orders:
        total_money = o.get("total_money") or {}
        total_cents += total_money.get("amount", 0)
        line_items = o.get("line_items") or []
        for li in line_items:
            total_items += int(li.get("quantity", "0") or "0")

    data = [{
        "period": f"Last {days} days",
        "orders": len(orders),
        "items_sold": total_items,
        "revenue": format_money(total_cents),
        "avg_order": format_money(total_cents // len(orders)) if orders else "$0.00",
    }]
    print_output(
        data,
        columns=[
            ("period", "Period"),
            ("orders", "Orders"),
            ("items_sold", "Items Sold"),
            ("revenue", "Revenue"),
            ("avg_order", "Avg Order"),
        ],
        fmt=fmt,
        title="Sales Summary",
    )


def _report_by_item(orders: list[dict], fmt: str, top: int | None, bottom: int | None) -> None:
    """Breakdown by catalog item."""
    item_stats: dict[str, dict] = defaultdict(lambda: {"units": 0, "revenue_cents": 0})

    for o in orders:
        for li in o.get("line_items") or []:
            name = li.get("name", "Unknown")
            qty = int(li.get("quantity", "0") or "0")
            total = (li.get("total_money") or {}).get("amount", 0)
            item_stats[name]["units"] += qty
            item_stats[name]["revenue_cents"] += total

    data = []
    for name, stats in item_stats.items():
        avg = stats["revenue_cents"] // stats["units"] if stats["units"] else 0
        data.append({
            "name": name,
            "units": stats["units"],
            "revenue": format_money(stats["revenue_cents"]),
            "revenue_cents": stats["revenue_cents"],
            "avg_price": format_money(avg),
        })

    data.sort(key=lambda x: x["revenue_cents"], reverse=True)

    if top:
        data = data[:top]
    elif bottom:
        data = data[-bottom:]

    columns = [
        ("name", "Product"),
        ("units", "Units"),
        ("revenue", "Revenue"),
        ("avg_price", "Avg Price"),
    ]
    print_output(data, columns=columns, fmt=fmt, title="Sales by Item")


def _report_by_day(orders: list[dict], fmt: str) -> None:
    """Daily revenue trend."""
    day_stats: dict[str, dict] = defaultdict(lambda: {"orders": 0, "revenue_cents": 0})

    for o in orders:
        closed = o.get("closed_at") or o.get("created_at", "")
        day = closed[:10] if closed else "Unknown"
        total = (o.get("total_money") or {}).get("amount", 0)
        day_stats[day]["orders"] += 1
        day_stats[day]["revenue_cents"] += total

    data = []
    for day in sorted(day_stats.keys()):
        stats = day_stats[day]
        data.append({
            "date": day,
            "orders": stats["orders"],
            "revenue": format_money(stats["revenue_cents"]),
            "revenue_cents": stats["revenue_cents"],
        })

    columns = [("date", "Date"), ("orders", "Orders"), ("revenue", "Revenue")]
    print_output(data, columns=columns, fmt=fmt, title="Sales by Day")


def _report_by_hour(orders: list[dict], fmt: str) -> None:
    """Hourly breakdown (peak hours)."""
    hour_stats: dict[int, dict] = defaultdict(lambda: {"orders": 0, "revenue_cents": 0})

    for o in orders:
        closed = o.get("closed_at") or o.get("created_at", "")
        if closed and len(closed) >= 13:
            try:
                hour = int(closed[11:13])
                total = (o.get("total_money") or {}).get("amount", 0)
                hour_stats[hour]["orders"] += 1
                hour_stats[hour]["revenue_cents"] += total
            except ValueError:
                pass

    data = []
    for hour in sorted(hour_stats.keys()):
        stats = hour_stats[hour]
        label = f"{hour:02d}:00"
        data.append({
            "hour": label,
            "orders": stats["orders"],
            "revenue": format_money(stats["revenue_cents"]),
        })

    columns = [("hour", "Hour"), ("orders", "Orders"), ("revenue", "Revenue")]
    print_output(data, columns=columns, fmt=fmt, title="Sales by Hour")


def _report_by_payment_method(orders: list[dict], fmt: str) -> None:
    """Breakdown by payment method."""
    method_stats: dict[str, dict] = defaultdict(lambda: {"orders": 0, "revenue_cents": 0})

    for o in orders:
        tenders = o.get("tenders") or []
        total = (o.get("total_money") or {}).get("amount", 0)
        if tenders:
            for t in tenders:
                method = t.get("type", "UNKNOWN")
                tender_amount = (t.get("amount_money") or {}).get("amount", 0)
                method_stats[method]["orders"] += 1
                method_stats[method]["revenue_cents"] += tender_amount
        else:
            method_stats["UNKNOWN"]["orders"] += 1
            method_stats["UNKNOWN"]["revenue_cents"] += total

    data = []
    for method, stats in sorted(method_stats.items(), key=lambda x: x[1]["revenue_cents"], reverse=True):
        data.append({
            "method": method.replace("_", " ").title(),
            "orders": stats["orders"],
            "revenue": format_money(stats["revenue_cents"]),
        })

    columns = [("method", "Method"), ("orders", "Transactions"), ("revenue", "Revenue")]
    print_output(data, columns=columns, fmt=fmt, title="Sales by Payment Method")


def _report_by_category(orders: list[dict], fmt: str) -> None:
    """Breakdown by category."""
    cat_stats: dict[str, dict] = defaultdict(lambda: {"units": 0, "revenue_cents": 0})

    for o in orders:
        for li in o.get("line_items") or []:
            cat = li.get("catalog_object_id", "Uncategorized")
            # Use variation name as fallback category
            name = li.get("name", "Unknown")
            qty = int(li.get("quantity", "0") or "0")
            total = (li.get("total_money") or {}).get("amount", 0)
            cat_stats[name]["units"] += qty
            cat_stats[name]["revenue_cents"] += total

    data = []
    for cat, stats in sorted(cat_stats.items(), key=lambda x: x[1]["revenue_cents"], reverse=True):
        data.append({
            "category": cat,
            "units": stats["units"],
            "revenue": format_money(stats["revenue_cents"]),
        })

    columns = [("category", "Category"), ("units", "Units"), ("revenue", "Revenue")]
    print_output(data, columns=columns, fmt=fmt, title="Sales by Category")
