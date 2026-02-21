"""System/runtime/position/order CLI commands (step 37)."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from rich.table import Table

from src.cli_context import (
    CLICommandError,
    CLIContext,
    console,
    read_runtime_state,
    write_runtime_state,
)
from src.core.enums import OrderSide, OrderStatus


def handle_start(ctx: CLIContext, _args: Any) -> int:
    state = read_runtime_state(ctx.config)
    if state.get("running"):
        raise CLICommandError("系统已是运行状态，如需重置请先执行 stop")

    path = write_runtime_state(
        ctx.config,
        {
            "running": True,
            "mode": "initialized",
            "database_path": str(ctx.database.database_path),
        },
    )
    console.print(f"[green]启动完成[/green]，运行状态文件: {path}")
    return 0


def handle_stop(ctx: CLIContext, _args: Any) -> int:
    path = write_runtime_state(
        ctx.config,
        {
            "running": False,
            "mode": "stopped",
            "database_path": str(ctx.database.database_path),
        },
    )
    console.print(f"[yellow]已停止[/yellow]，运行状态文件: {path}")
    return 0


def handle_status(ctx: CLIContext, args: Any) -> int:
    state = read_runtime_state(ctx.config)

    with ctx.database.transaction() as tx:
        metrics = {
            "accounts": _count_rows(tx, "accounts"),
            "orders": _count_rows(tx, "orders"),
            "open_orders": _count_open_orders(tx),
            "trades": _count_rows(tx, "trades"),
            "positions": _count_rows(tx, "positions"),
            "candles": _count_rows(tx, "candles"),
        }

    table = Table(title="系统状态")
    table.add_column("项目")
    table.add_column("值", justify="right")
    table.add_row("running", str(bool(state.get("running"))))
    table.add_row("database", str(ctx.database.database_path))
    for key, value in metrics.items():
        table.add_row(key, str(value))
    console.print(table)

    if args.disk:
        _print_disk_status(ctx.database.database_path)
    return 0


def handle_balance(ctx: CLIContext, _args: Any) -> int:
    accounts = ctx.account_service.list_accounts()
    positions = ctx.account_service.load_positions()

    table = Table(title="账户余额")
    table.add_column("币种")
    table.add_column("可用", justify="right")
    table.add_column("冻结", justify="right")
    table.add_column("余额", justify="right")

    base_currency = ctx.account_service.base_currency
    base_cash = 0.0
    for account in accounts:
        if account.currency == base_currency:
            base_cash = account.available + account.frozen
        table.add_row(
            account.currency,
            f"{account.available:.8f}",
            f"{account.frozen:.8f}",
            f"{account.balance:.8f}",
        )

    positions_value = sum(
        position.amount * (position.current_price if position.current_price is not None else position.entry_price)
        for position in positions
    )
    estimated_total = base_cash + positions_value

    console.print(table)
    console.print(
        f"base_currency={base_currency} | base_cash={base_cash:.8f} | "
        f"positions_value={positions_value:.8f} | estimated_total_assets={estimated_total:.8f}"
    )
    return 0


def handle_positions(ctx: CLIContext, _args: Any) -> int:
    positions = ctx.account_service.load_positions()
    table = Table(title="当前持仓")
    table.add_column("symbol")
    table.add_column("amount", justify="right")
    table.add_column("entry", justify="right")
    table.add_column("current", justify="right")
    table.add_column("unrealized", justify="right")
    table.add_column("realized", justify="right")

    for position in positions:
        table.add_row(
            position.symbol,
            f"{position.amount:.8f}",
            f"{position.entry_price:.8f}",
            f"{(position.current_price or 0.0):.8f}",
            f"{(position.unrealized_pnl or 0.0):.8f}",
            f"{position.realized_pnl:.8f}",
        )
    console.print(table)
    return 0


def handle_cleanup(ctx: CLIContext, args: Any) -> int:
    if args.days <= 0:
        raise CLICommandError("days 必须 > 0")

    cutoff_ms = int(time.time() * 1000) - args.days * 24 * 3600 * 1000
    with ctx.database.transaction() as tx:
        before = tx.total_changes
        tx.execute("DELETE FROM candles WHERE timestamp < ?;", (cutoff_ms,))
        deleted = tx.total_changes - before

    console.print(f"[green]清理完成[/green] deleted_candles={deleted} cutoff_ms={cutoff_ms}")
    return 0


def handle_reconcile(ctx: CLIContext, _args: Any) -> int:
    with ctx.database.transaction() as tx:
        rows = tx.execute(
            """
            SELECT o.symbol, o.side, t.price, t.amount
            FROM trades t
            INNER JOIN orders o ON o.id = t.order_id
            ORDER BY t.timestamp ASC, t.id ASC;
            """
        ).fetchall()

        states: dict[str, dict[str, float]] = {}
        for row in rows:
            symbol = str(row["symbol"])
            side = str(row["side"])
            price = float(row["price"])
            amount = float(row["amount"])
            state = states.setdefault(symbol, {"amount": 0.0, "entry": 0.0, "realized": 0.0})

            if side == OrderSide.BUY.value:
                new_amount = state["amount"] + amount
                state["entry"] = (
                    ((state["amount"] * state["entry"]) + (amount * price)) / new_amount
                    if new_amount > 0
                    else price
                )
                state["amount"] = new_amount
                continue

            if amount > state["amount"] + 1e-9:
                raise CLICommandError(f"reconcile 失败: {symbol} 卖出数量超过持仓")
            state["realized"] += (price - state["entry"]) * amount
            state["amount"] = max(0.0, state["amount"] - amount)

        tx.execute("DELETE FROM positions;")
        inserted = 0
        for symbol, state in states.items():
            if state["amount"] <= 1e-12:
                continue
            tx.execute(
                """
                INSERT INTO positions(symbol, amount, entry_price, current_price, unrealized_pnl, realized_pnl, opened_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
                """,
                (symbol, state["amount"], state["entry"], state["entry"], 0.0, state["realized"]),
            )
            inserted += 1

    console.print(f"[green]reconcile 完成[/green] rebuilt_positions={inserted}")
    return 0


def _print_disk_status(database_path: Path) -> None:
    disk = shutil.disk_usage(database_path.parent)
    db_size = database_path.stat().st_size if database_path.exists() else 0

    table = Table(title="磁盘状态")
    table.add_column("项目")
    table.add_column("值", justify="right")
    table.add_row("db_file", str(database_path))
    table.add_row("db_size_bytes", str(db_size))
    table.add_row("disk_total_bytes", str(disk.total))
    table.add_row("disk_used_bytes", str(disk.used))
    table.add_row("disk_free_bytes", str(disk.free))
    console.print(table)


def _count_rows(tx: Any, table: str) -> int:
    row = tx.execute(f"SELECT COUNT(1) AS cnt FROM {table};").fetchone()
    return int(row["cnt"]) if row is not None else 0


def _count_open_orders(tx: Any) -> int:
    row = tx.execute(
        """
        SELECT COUNT(1) AS cnt
        FROM orders
        WHERE status IN (?, ?);
        """,
        (OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value),
    ).fetchone()
    return int(row["cnt"]) if row is not None else 0
