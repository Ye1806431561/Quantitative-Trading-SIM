"""Backtest result exporter (step 28)."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.backtest.result_models import BacktestRunResult, TradeRecord  # noqa: F401


class BacktestExporterError(RuntimeError):
    """Raised when export operation fails."""


class BacktestResultExporter:
    """Export backtest results to CSV and JSON formats (step 28)."""

    def __init__(self, output_dir: str | Path) -> None:
        """Initialize exporter with output directory."""
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_summary_json(
        self,
        result: BacktestRunResult,
        filename: str = "backtest_summary.json",
    ) -> Path:
        """Export backtest summary report to JSON."""
        output_path = self._output_dir / filename
        summary = self._build_summary_dict(result)
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export JSON summary: {exc}") from exc
        
        return output_path

    def export_summary_csv(
        self,
        result: BacktestRunResult,
        filename: str = "backtest_summary.csv",
    ) -> Path:
        """Export backtest summary report to CSV (flattened structure)."""
        output_path = self._output_dir / filename
        summary = self._build_summary_dict(result)
        flattened = self._flatten_dict(summary)
        
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Metric", "Value"])
                for key, value in flattened.items():
                    writer.writerow([key, value])
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export CSV summary: {exc}") from exc
        
        return output_path

    def export_equity_curve_json(
        self,
        result: BacktestRunResult,
        filename: str = "equity_curve.json",
    ) -> Path:
        """Export time series returns (equity curve) to JSON."""
        output_path = self._output_dir / filename
        
        equity_data = {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "initial_capital": result.initial_capital,
            "time_series": result.time_series_returns,
        }
        
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(equity_data, f, indent=2, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export equity curve JSON: {exc}") from exc
        
        return output_path

    def export_equity_curve_csv(
        self,
        result: BacktestRunResult,
        filename: str = "equity_curve.csv",
    ) -> Path:
        """Export time series returns (equity curve) to CSV."""
        output_path = self._output_dir / filename
        
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Return"])
                for timestamp, return_value in sorted(result.time_series_returns.items()):
                    writer.writerow([timestamp, return_value])
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export equity curve CSV: {exc}") from exc
        
        return output_path

    def export_all(
        self,
        result: BacktestRunResult,
        prefix: str = "",
    ) -> dict[str, Path]:
        """Export all backtest results (summary + equity curve + trade log) in both formats."""
        suffix = f"_{prefix}" if prefix else ""

        paths = {
            "summary_json": self.export_summary_json(
                result,
                f"backtest_summary{suffix}.json",
            ),
            "summary_csv": self.export_summary_csv(
                result,
                f"backtest_summary{suffix}.csv",
            ),
            "equity_json": self.export_equity_curve_json(
                result,
                f"equity_curve{suffix}.json",
            ),
            "equity_csv": self.export_equity_curve_csv(
                result,
                f"equity_curve{suffix}.csv",
            ),
            "trade_log_json": self.export_trade_log_json(
                result,
                f"trade_log{suffix}.json",
            ),
            "trade_log_csv": self.export_trade_log_csv(
                result,
                f"trade_log{suffix}.csv",
            ),
        }

        return paths

    def export_trade_log_json(
        self,
        result: BacktestRunResult,
        filename: str = "trade_log.json",
    ) -> Path:
        """Export individual trade records to JSON (step 28)."""
        output_path = self._output_dir / filename
        trade_data = {
            "symbol": result.symbol,
            "timeframe": result.timeframe,
            "total_trades": len(result.trade_log),
            "trades": [
                {
                    "entry_time": record.entry_time,
                    "exit_time": record.exit_time,
                    "side": record.side,
                    "size": record.size,
                    "entry_price": record.entry_price,
                    "exit_price": record.exit_price,
                    "pnl_gross": record.pnl_gross,
                    "pnl_net": record.pnl_net,
                }
                for record in result.trade_log
            ],
        }
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(trade_data, f, indent=2, ensure_ascii=False)
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export trade log JSON: {exc}") from exc
        return output_path

    def export_trade_log_csv(
        self,
        result: BacktestRunResult,
        filename: str = "trade_log.csv",
    ) -> Path:
        """Export individual trade records to CSV (step 28)."""
        output_path = self._output_dir / filename
        try:
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "entry_time", "exit_time", "side", "size",
                    "entry_price", "exit_price", "pnl_gross", "pnl_net",
                ])
                for record in result.trade_log:
                    writer.writerow([
                        record.entry_time, record.exit_time, record.side,
                        record.size, record.entry_price, record.exit_price,
                        record.pnl_gross, record.pnl_net,
                    ])
        except (OSError, TypeError) as exc:
            raise BacktestExporterError(f"Failed to export trade log CSV: {exc}") from exc
        return output_path

    @staticmethod
    def _build_summary_dict(result: BacktestRunResult) -> dict[str, Any]:
        """Build summary dictionary from BacktestRunResult."""
        return {
            "basic_info": {
                "symbol": result.symbol,
                "timeframe": result.timeframe,
                "data_source": result.data_source,
                "bars_processed": result.bars_processed,
            },
            "capital": {
                "initial_capital": result.initial_capital,
                "final_value": result.final_value,
                "pnl": result.pnl,
                "total_return_pct": result.total_return_pct,
            },
            "trade_statistics": asdict(result.trade_stats),
            "risk_metrics": asdict(result.risk_metrics),
            "returns_analysis": asdict(result.returns_analysis),
        }

    @staticmethod
    def _flatten_dict(nested: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
        """Flatten nested dictionary for CSV export.

        None values are serialized as the string 'None' to distinguish them
        from empty strings in CSV output.
        """
        items: list[tuple[str, Any]] = []

        for key, value in nested.items():
            new_key = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                items.extend(
                    BacktestResultExporter._flatten_dict(value, new_key).items()
                )
            else:
                # Explicitly convert None to 'None' string for unambiguous CSV serialization
                items.append((new_key, "None" if value is None else value))

        return dict(items)

