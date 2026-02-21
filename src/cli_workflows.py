"""Backtest/data/live workflow CLI commands (step 37)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from rich.table import Table

from src.backtest.engine import BacktestEngine
from src.backtest.exporter import BacktestResultExporter
from src.backtest.result_models import BacktestRunRequest
from src.analysis.visualization import PerformanceVisualizer, VisualizationError
from src.cli_context import (
    CLICommandError,
    CLIContext,
    console,
    parse_param_pairs,
    resolve_time_range_ms,
    write_runtime_state,
)
from src.data.market import MarketDataFetcher
from src.data.storage import CandleDownloadRequest, HistoricalCandleStorage
from src.live.realtime_loop import RealtimeSimulationLoop
from src.strategies.factory import create_live_strategy
from src.strategies.registry import StrategyRegistry
from src.utils.config_defaults import ALLOWED_TIMEFRAMES


class _NoopFetcher:
    def fetch_ohlcv(self, *_args: Any, **_kwargs: Any) -> list[list[Any]]:
        return []


def handle_backtest(ctx: CLIContext, args: Any) -> int:
    registry = StrategyRegistry.default()
    try:
        strategy_spec = registry.get_by_name(args.strategy)
    except Exception as exc:
        raise CLICommandError(str(exc)) from exc

    params = parse_param_pairs(args.param)
    timeframe = args.timeframe or str(ctx.config.get("backtest", {}).get("default_timeframe", "1h"))
    start_ms, end_ms = resolve_time_range_ms(
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        days=args.days,
    )

    trading_cfg = ctx.config.get("trading", {})
    commission_cfg = trading_cfg.get("commission", {}) if isinstance(trading_cfg, dict) else {}
    engine = BacktestEngine(
        database=ctx.database,
        initial_capital=float(ctx.config.get("account", {}).get("initial_capital", 10000.0)),
        commission_rate=float(commission_cfg.get("taker", 0.001)),
        slippage_rate=float(trading_cfg.get("slippage", 0.0)) if isinstance(trading_cfg, dict) else 0.0,
        data_read_source=str(ctx.config.get("backtest", {}).get("data_read_source", "sqlite")),
        strategies_config=ctx.strategies_config,
        strategy_registry=registry,
    )

    result = engine.run(
        BacktestRunRequest(
            symbol=args.symbol,
            timeframe=timeframe,
            start_timestamp=start_ms,
            end_timestamp=end_ms,
            strategy_class=strategy_spec.strategy_class,
            strategy_params=params,
        )
    )

    table = Table(title="回测结果")
    table.add_column("指标")
    table.add_column("值", justify="right")
    table.add_row("symbol", result.symbol)
    table.add_row("timeframe", result.timeframe)
    table.add_row("bars_processed", str(result.bars_processed))
    table.add_row("initial_capital", f"{result.initial_capital:.4f}")
    table.add_row("final_value", f"{result.final_value:.4f}")
    table.add_row("pnl", f"{result.pnl:.4f}")
    table.add_row("total_return_pct", f"{result.total_return_pct:.4f}")
    table.add_row("trades", str(result.trade_stats.total_trades))
    table.add_row("max_drawdown_pct", f"{result.risk_metrics.max_drawdown_pct:.4f}")
    table.add_row("sharpe_ratio", str(result.risk_metrics.sharpe_ratio))
    console.print(table)

    if args.output_dir:
        exporter = BacktestResultExporter(args.output_dir)
        paths = exporter.export_all(result=result, prefix=args.prefix or "")
        
        try:
            visualizer = PerformanceVisualizer(args.output_dir)
            
            # Reconstruct absolute equity curve from time_series_returns
            equity_curve: list[tuple[str, float]] = []
            current_equity = result.initial_capital
            
            for ts, ret in result.time_series_returns.items():
                current_equity *= (1.0 + ret)
                equity_curve.append((ts, current_equity))

            chart_artifacts = visualizer.export_all(
                equity_curve=equity_curve,
                trade_log=result.trade_log,
                prefix=args.prefix or "",
            )
            paths["equity_curve_chart"] = chart_artifacts.equity_curve_path
            paths["drawdown_curve_chart"] = chart_artifacts.drawdown_curve_path
            paths["trade_distribution_chart"] = chart_artifacts.trade_distribution_path
            paths["holding_time_chart"] = chart_artifacts.holding_time_path
        except VisualizationError as exc:
            console.print(f"[yellow]无法生成可视化图表[/yellow]: {exc}")
            
        console.print({name: str(path) for name, path in paths.items()})

    return 0


def handle_download(ctx: CLIContext, args: Any) -> int:
    start_ms, end_ms = resolve_time_range_ms(
        start_ms=args.start_ms,
        end_ms=args.end_ms,
        days=args.days,
    )
    fetcher = MarketDataFetcher.from_config(ctx.config)
    storage = HistoricalCandleStorage(ctx.database, fetcher)
    result = storage.download_and_store(
        CandleDownloadRequest(
            symbol=args.symbol,
            timeframe=args.timeframe,
            start_timestamp=start_ms,
            end_timestamp=end_ms,
            batch_size=args.batch_size,
        )
    )

    console.print(
        "[green]下载完成[/green] "
        f"dataset={result.dataset_name} downloaded_count={result.downloaded_count}"
    )
    return 0


def handle_live(ctx: CLIContext, args: Any) -> int:
    explicit_params = parse_param_pairs(args.param)
    strategy, merged_params = create_live_strategy(
        strategy_name=args.strategy,
        strategies_config=ctx.strategies_config,
        explicit_params=explicit_params,
    )
    loop = RealtimeSimulationLoop.from_config(
        config=ctx.config,
        database=ctx.database,
        strategy=strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        tick_interval_seconds=args.tick_interval,
        max_iterations=args.max_iterations,
        strategy_params=merged_params,
    )

    console.print(
        f"[green]实时模拟启动[/green] strategy={args.strategy} symbol={args.symbol} timeframe={args.timeframe}"
    )
    write_runtime_state(
        ctx.config,
        {
            "running": True,
            "mode": "live",
            "strategy": args.strategy,
            "symbol": args.symbol,
            "timeframe": args.timeframe,
        },
    )
    try:
        loop.start()
    except KeyboardInterrupt:
        loop.stop()
        console.print("[yellow]收到中断信号，已停止实时模拟[/yellow]")
    finally:
        write_runtime_state(
            ctx.config,
            {
                "running": False,
                "mode": "idle",
                "strategy": args.strategy,
                "symbol": args.symbol,
                "timeframe": args.timeframe,
                "iteration_count": loop.iteration_count,
            },
        )

    console.print(f"实时模拟结束，iteration_count={loop.iteration_count}")
    return 0


def handle_import(ctx: CLIContext, args: Any) -> int:
    csv_path = Path(args.file)
    if not csv_path.exists():
        raise CLICommandError(f"导入文件不存在: {csv_path}")

    rows = _read_candles_from_csv(csv_path, default_symbol=args.symbol, default_timeframe=args.timeframe)
    with ctx.database.transaction() as tx:
        before = tx.total_changes
        tx.executemany(
            """
            INSERT OR IGNORE INTO candles(symbol, timeframe, timestamp, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            rows,
        )
        inserted = tx.total_changes - before

    console.print(
        f"[green]导入完成[/green] file={csv_path} parsed={len(rows)} inserted={inserted}"
    )
    return 0


def handle_export(ctx: CLIContext, args: Any) -> int:
    if args.start_ms is not None and args.end_ms is not None and args.start_ms > args.end_ms:
        raise CLICommandError("start-ms 不能大于 end-ms")

    sql = [
        "SELECT symbol, timeframe, timestamp, open, high, low, close, volume",
        "FROM candles",
        "WHERE symbol = ? AND timeframe = ?",
    ]
    params: list[Any] = [args.symbol.strip().upper(), args.timeframe]
    if args.start_ms is not None:
        sql.append("AND timestamp >= ?")
        params.append(args.start_ms)
    if args.end_ms is not None:
        sql.append("AND timestamp <= ?")
        params.append(args.end_ms)
    sql.append("ORDER BY timestamp ASC")

    with ctx.database.transaction() as tx:
        rows = tx.execute(" ".join(sql), params).fetchall()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"])
        for row in rows:
            writer.writerow(
                [
                    row["symbol"],
                    row["timeframe"],
                    row["timestamp"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["volume"],
                ]
            )

    console.print(f"[green]导出完成[/green] rows={len(rows)} output={output}")
    return 0


def _read_candles_from_csv(
    csv_path: Path,
    *,
    default_symbol: str | None,
    default_timeframe: str | None,
) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
            raise CLICommandError("CSV 缺少必要列: timestamp/open/high/low/close/volume")

        for line_no, row in enumerate(reader, start=2):
            symbol = (row.get("symbol") or default_symbol or "").strip().upper()
            timeframe = (row.get("timeframe") or default_timeframe or "").strip()
            if not symbol:
                raise CLICommandError(f"第 {line_no} 行缺少 symbol，且未提供 --symbol")
            if timeframe not in ALLOWED_TIMEFRAMES:
                raise CLICommandError(f"第 {line_no} 行 timeframe 非法: {timeframe}")

            try:
                timestamp = int(row["timestamp"])
                open_price = float(row["open"])
                high = float(row["high"])
                low = float(row["low"])
                close = float(row["close"])
                volume = float(row["volume"])
            except (TypeError, ValueError) as exc:
                raise CLICommandError(f"第 {line_no} 行数据格式错误") from exc

            rows.append((symbol, timeframe, timestamp, open_price, high, low, close, volume))

    return rows


def ensure_export_storage(ctx: CLIContext) -> HistoricalCandleStorage:
    """Utility kept for compatibility with workflow commands."""
    return HistoricalCandleStorage(ctx.database, _NoopFetcher())
