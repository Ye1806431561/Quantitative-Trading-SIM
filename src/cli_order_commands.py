"""Order-related CLI commands (step 37)."""

from __future__ import annotations

from typing import Any, Mapping

from rich.table import Table

from src.cli_context import CLICommandError, CLIContext, console
from src.core.enums import OrderSide, OrderStatus, OrderType
from src.core.execution_cost import ExecutionCostProfile
from src.core.limit_matching import LimitOrderMatchingEngine, LimitOrderRequest
from src.core.matching import MarketOrderRequest, MatchingEngine
from src.core.risk import RiskLimits
from src.core.stop_trigger import StopTriggerEngine, TriggerOrderRequest
from src.data.realtime_market import RealtimeMarketDataService


def handle_order_place(ctx: CLIContext, args: Any) -> int:
    side = OrderSide(args.side)
    order_type = OrderType(args.type)
    market_service, cost_profile, risk_limits = _build_execution_dependencies(ctx)

    if order_type == OrderType.MARKET:
        engine = MatchingEngine(
            database=ctx.database,
            account_service=ctx.account_service,
            order_service=ctx.order_service,
            trade_service=ctx.trade_service,
            market_reader=market_service,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
        )
        result = engine.execute_market_order(
            MarketOrderRequest(symbol=args.symbol, side=side, amount=args.amount)
        )
        console.print(
            f"[green]市价单成交[/green] order_id={result.order.id} price={result.execution_price:.8f}"
        )
        return 0

    if order_type == OrderType.LIMIT:
        if args.price is None:
            raise CLICommandError("限价单必须提供 --price")
        engine = LimitOrderMatchingEngine(
            database=ctx.database,
            account_service=ctx.account_service,
            order_service=ctx.order_service,
            trade_service=ctx.trade_service,
            market_reader=market_service,
            cost_profile=cost_profile,
            risk_limits=risk_limits,
        )
        order = engine.place_limit_order(
            LimitOrderRequest(
                symbol=args.symbol,
                side=side,
                amount=args.amount,
                limit_price=args.price,
            )
        )
        console.print(f"[green]限价单已挂单[/green] order_id={order.id}")
        return 0

    trigger_price = args.trigger_price if args.trigger_price is not None else args.price
    if trigger_price is None:
        raise CLICommandError("触发单必须提供 --trigger-price（或 --price）")

    engine = StopTriggerEngine(
        database=ctx.database,
        account_service=ctx.account_service,
        order_service=ctx.order_service,
        trade_service=ctx.trade_service,
        market_reader=market_service,
        cost_profile=cost_profile,
        risk_limits=risk_limits,
    )
    order = engine.place_trigger_order(
        TriggerOrderRequest(
            symbol=args.symbol,
            type=order_type,
            side=side,
            amount=args.amount,
            trigger_price=trigger_price,
        )
    )
    console.print(f"[green]触发单已创建[/green] order_id={order.id}")
    return 0


def handle_order_list(ctx: CLIContext, args: Any) -> int:
    status = OrderStatus(args.status) if args.status else None
    orders = ctx.order_service.list_orders(symbol=args.symbol, status=status, limit=args.limit)

    table = Table(title="订单列表")
    table.add_column("id")
    table.add_column("symbol")
    table.add_column("type")
    table.add_column("side")
    table.add_column("amount", justify="right")
    table.add_column("filled", justify="right")
    table.add_column("status")
    for item in orders:
        table.add_row(
            item.id,
            item.symbol,
            item.type.value,
            item.side.value,
            f"{item.amount:.8f}",
            f"{item.filled:.8f}",
            item.status.value,
        )
    console.print(table)
    return 0


def handle_order_cancel(ctx: CLIContext, args: Any) -> int:
    order = ctx.order_service.cancel_order(args.order_id)
    console.print(f"[yellow]撤单完成[/yellow] order_id={order.id} status={order.status.value}")
    return 0


def _build_execution_dependencies(
    ctx: CLIContext,
) -> tuple[RealtimeMarketDataService, ExecutionCostProfile, RiskLimits]:
    market_service = RealtimeMarketDataService.from_config(ctx.config)
    trading = ctx.config.get("trading", {})
    commission = trading.get("commission", {}) if isinstance(trading, Mapping) else {}
    cost_profile = ExecutionCostProfile(
        maker_fee_rate=float(commission.get("maker", 0.001)),
        taker_fee_rate=float(commission.get("taker", 0.001)),
        slippage_rate=float(trading.get("slippage", 0.0)) if isinstance(trading, Mapping) else 0.0,
    )
    return market_service, cost_profile, RiskLimits.from_config(ctx.config)
