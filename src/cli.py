"""CLI entrypoint and argument parser (step 37)."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any

from src.cli_commands import (
    handle_balance,
    handle_cleanup,
    handle_positions,
    handle_reconcile,
    handle_start,
    handle_status,
    handle_stop,
)
from src.cli_context import CLICommandError, build_context, console
from src.cli_order_commands import handle_order_cancel, handle_order_list, handle_order_place
from src.cli_workflows import (
    handle_backtest,
    handle_download,
    handle_export,
    handle_import,
    handle_live,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quant-sim",
        description="虚拟货币量化交易模拟盘 CLI",
    )
    parser.add_argument("--config", default="config/config.yaml", help="主配置文件路径")
    parser.add_argument("--strategies", default="config/strategies.yaml", help="策略配置文件路径")
    parser.add_argument("--env", default=".env", help="环境变量文件路径")

    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", aliases=["startup"], help="初始化并标记系统启动")
    start_parser.set_defaults(handler=handle_start)

    stop_parser = subparsers.add_parser("stop", help="标记系统停止")
    stop_parser.set_defaults(handler=handle_stop)

    status_parser = subparsers.add_parser("status", help="查看系统状态")
    status_parser.add_argument("--disk", action="store_true", help="同时输出磁盘状态")
    status_parser.set_defaults(handler=handle_status)

    balance_parser = subparsers.add_parser("balance", help="查看账户余额")
    balance_parser.set_defaults(handler=handle_balance)

    positions_parser = subparsers.add_parser("positions", help="查看持仓")
    positions_parser.set_defaults(handler=handle_positions)

    order_parser = subparsers.add_parser("order", help="订单操作")
    order_subparsers = order_parser.add_subparsers(dest="order_command", required=True)

    order_place = order_subparsers.add_parser("place", help="下单")
    order_place.add_argument("--symbol", required=True)
    order_place.add_argument("--side", required=True, choices=["buy", "sell"])
    order_place.add_argument(
        "--type",
        required=True,
        choices=["market", "limit", "stop_loss", "take_profit"],
    )
    order_place.add_argument("--amount", required=True, type=float)
    order_place.add_argument("--price", type=float)
    order_place.add_argument("--trigger-price", type=float)
    order_place.set_defaults(handler=handle_order_place)

    order_list = order_subparsers.add_parser("list", help="查询订单")
    order_list.add_argument("--symbol")
    order_list.add_argument(
        "--status",
        choices=["pending", "open", "partially_filled", "filled", "canceled", "rejected"],
    )
    order_list.add_argument("--limit", type=int, default=50)
    order_list.set_defaults(handler=handle_order_list)

    order_cancel = order_subparsers.add_parser("cancel", help="撤单")
    order_cancel.add_argument("--order-id", required=True)
    order_cancel.set_defaults(handler=handle_order_cancel)

    backtest_parser = subparsers.add_parser("backtest", help="运行回测")
    backtest_parser.add_argument("--strategy", required=True)
    backtest_parser.add_argument("--symbol", required=True)
    backtest_parser.add_argument("--timeframe")
    backtest_parser.add_argument("--start-ms", type=int)
    backtest_parser.add_argument("--end-ms", type=int)
    backtest_parser.add_argument("--days", type=int)
    backtest_parser.add_argument("--param", action="append", help="策略参数，格式 key=value")
    backtest_parser.add_argument("--output-dir", help="可选：导出回测结果目录")
    backtest_parser.add_argument("--prefix", help="导出文件名前缀")
    backtest_parser.set_defaults(handler=handle_backtest)

    download_parser = subparsers.add_parser("download", help="下载历史K线到SQLite")
    download_parser.add_argument("--symbol", required=True)
    download_parser.add_argument("--timeframe", required=True)
    download_parser.add_argument("--start-ms", type=int)
    download_parser.add_argument("--end-ms", type=int)
    download_parser.add_argument("--days", type=int)
    download_parser.add_argument("--batch-size", type=int, default=500)
    download_parser.set_defaults(handler=handle_download)

    live_parser = subparsers.add_parser("live", help="运行实时模拟")
    live_parser.add_argument("--strategy", required=True)
    live_parser.add_argument("--symbol", required=True)
    live_parser.add_argument("--timeframe", required=True)
    live_parser.add_argument("--tick-interval", type=float, default=1.0)
    live_parser.add_argument("--max-iterations", type=int)
    live_parser.add_argument("--param", action="append", help="策略参数，格式 key=value")
    live_parser.set_defaults(handler=handle_live)

    import_parser = subparsers.add_parser("import", help="从CSV导入K线到SQLite")
    import_parser.add_argument("--file", required=True)
    import_parser.add_argument("--symbol", help="当CSV不含symbol列时使用")
    import_parser.add_argument("--timeframe", help="当CSV不含timeframe列时使用")
    import_parser.set_defaults(handler=handle_import)

    export_parser = subparsers.add_parser("export", help="从SQLite导出K线到CSV")
    export_parser.add_argument("--symbol", required=True)
    export_parser.add_argument("--timeframe", required=True)
    export_parser.add_argument("--output", required=True)
    export_parser.add_argument("--start-ms", type=int)
    export_parser.add_argument("--end-ms", type=int)
    export_parser.set_defaults(handler=handle_export)

    cleanup_parser = subparsers.add_parser("cleanup", help="清理过期K线")
    cleanup_parser.add_argument("--days", type=int, required=True)
    cleanup_parser.set_defaults(handler=handle_cleanup)

    reconcile_parser = subparsers.add_parser("reconcile", help="按成交重建持仓")
    reconcile_parser.set_defaults(handler=handle_reconcile)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return int(exc.code)

    context = None
    try:
        context = build_context(
            config_path=args.config,
            strategies_path=args.strategies,
            env_path=args.env,
        )
        handler = getattr(args, "handler", None)
        if not callable(handler):
            raise CLICommandError("未找到命令处理器")
        return int(handler(context, args))
    except CLICommandError as exc:
        console.print(f"[bold red]命令执行失败[/bold red] {exc}")
        return 1
    except Exception as exc:  # pragma: no cover - safety net
        console.print(f"[bold red]未预期异常[/bold red] {exc}")
        return 1
    finally:
        if context is not None:
            context.close()


def entrypoint() -> int:
    """Console-script compatible entrypoint."""
    return main()
