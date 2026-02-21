"""Visualization exporter for performance analysis (Phase 4 Step 36)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib

# Use non-interactive backend for headless test/runtime environments.
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class VisualizationError(RuntimeError):
    """Raised when visualization export fails."""


@dataclass(frozen=True)
class VisualizationArtifacts:
    equity_curve_path: Path
    drawdown_curve_path: Path
    trade_distribution_path: Path
    holding_time_path: Path


class PerformanceVisualizer:
    """Export performance visualizations to local image files."""

    def __init__(self, output_dir: str | Path) -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def export_all(
        self,
        *,
        equity_curve: Mapping[object, float] | Sequence[tuple[object, float]],
        trade_log: Sequence[Mapping[str, object]] | Sequence[object] | None = None,
        prefix: str = "",
    ) -> VisualizationArtifacts:
        normalized_equity = _normalize_equity_series(equity_curve)
        suffix = f"_{prefix}" if prefix else ""

        equity_curve_path = self._output_dir / f"equity_curve{suffix}.png"
        drawdown_curve_path = self._output_dir / f"drawdown_curve{suffix}.png"
        trade_distribution_path = self._output_dir / f"trade_distribution{suffix}.png"
        holding_time_path = self._output_dir / f"holding_time{suffix}.png"

        self._plot_equity_curve(normalized_equity, equity_curve_path)
        self._plot_drawdown_curve(normalized_equity, drawdown_curve_path)
        self._plot_trade_distribution(trade_log or [], trade_distribution_path)
        self._plot_holding_time(trade_log or [], holding_time_path)

        return VisualizationArtifacts(
            equity_curve_path=equity_curve_path,
            drawdown_curve_path=drawdown_curve_path,
            trade_distribution_path=trade_distribution_path,
            holding_time_path=holding_time_path,
        )

    def _plot_equity_curve(
        self,
        equity_series: Sequence[tuple[float, float]],
        output_path: Path,
    ) -> None:
        timestamps = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts, _ in equity_series]
        values = [equity for _, equity in equity_series]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, values, color="tab:blue", linewidth=1.8)
        ax.set_title("Equity Curve")
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("Equity")
        ax.grid(True, alpha=0.25)
        fig.autofmt_xdate()
        self._save_figure(fig, output_path)

    def _plot_drawdown_curve(
        self,
        equity_series: Sequence[tuple[float, float]],
        output_path: Path,
    ) -> None:
        timestamps = [datetime.fromtimestamp(ts, tz=timezone.utc) for ts, _ in equity_series]
        drawdown_values = _compute_drawdown_series(equity_series)

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(timestamps, drawdown_values, color="tab:red", linewidth=1.8)
        ax.fill_between(timestamps, drawdown_values, alpha=0.2, color="tab:red")
        ax.set_title("Drawdown Curve")
        ax.set_xlabel("Time (UTC)")
        ax.set_ylabel("Drawdown")
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.25)
        fig.autofmt_xdate()
        self._save_figure(fig, output_path)

    def _plot_trade_distribution(
        self,
        trade_log: Sequence[Mapping[str, object]] | Sequence[object],
        output_path: Path,
    ) -> None:
        pnls = _extract_trade_pnls(trade_log)

        fig, ax = plt.subplots(figsize=(8, 4))
        if pnls:
            bins = min(20, max(5, len(pnls)))
            ax.hist(pnls, bins=bins, color="tab:green", alpha=0.75, edgecolor="black")
            ax.axvline(0.0, color="black", linestyle="--", linewidth=1)
        else:
            ax.text(
                0.5,
                0.5,
                "No trades available",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
        ax.set_title("Trade PnL Distribution")
        ax.set_xlabel("PnL")
        ax.set_ylabel("Count")
        ax.grid(True, alpha=0.2)
        self._save_figure(fig, output_path)

    def _plot_holding_time(
        self,
        trade_log: Sequence[Mapping[str, object]] | Sequence[object],
        output_path: Path,
    ) -> None:
        holding_hours = _extract_holding_hours(trade_log)

        fig, ax = plt.subplots(figsize=(8, 4))
        if holding_hours:
            bins = min(20, max(5, len(holding_hours)))
            ax.hist(
                holding_hours,
                bins=bins,
                color="tab:purple",
                alpha=0.75,
                edgecolor="black",
            )
        else:
            ax.text(
                0.5,
                0.5,
                "No holding-time data",
                transform=ax.transAxes,
                ha="center",
                va="center",
            )
        ax.set_title("Holding Time Distribution")
        ax.set_xlabel("Holding Time (hours)")
        ax.set_ylabel("Count")
        ax.grid(True, alpha=0.2)
        self._save_figure(fig, output_path)

    @staticmethod
    def _save_figure(fig: plt.Figure, output_path: Path) -> None:
        try:
            fig.tight_layout()
            fig.savefig(output_path, dpi=120)
        except OSError as exc:
            raise VisualizationError(f"failed to save image: {output_path}") from exc
        finally:
            plt.close(fig)


def _normalize_equity_series(
    series: Mapping[object, float] | Sequence[tuple[object, float]],
) -> list[tuple[float, float]]:
    if isinstance(series, Mapping):
        items = list(series.items())
    else:
        items = list(series)

    if len(items) < 2:
        raise VisualizationError("equity_curve must contain at least two points")

    normalized: list[tuple[float, float]] = []
    for raw_ts, raw_equity in items:
        if not isinstance(raw_equity, (int, float)) or isinstance(raw_equity, bool):
            raise VisualizationError("equity value must be numeric")
        normalized.append((_parse_timestamp(raw_ts), float(raw_equity)))

    normalized.sort(key=lambda item: item[0])
    return normalized


def _parse_timestamp(raw_value: object) -> float:
    if isinstance(raw_value, bool):
        raise VisualizationError("timestamp must be int, float, or ISO 8601 string")
    if isinstance(raw_value, datetime):
        if raw_value.tzinfo is None:
            raw_value = raw_value.replace(tzinfo=timezone.utc)
        return raw_value.timestamp()
    if isinstance(raw_value, (int, float)):
        numeric = float(raw_value)
        if numeric <= 0:
            raise VisualizationError("timestamp must be positive")
        return numeric / 1000.0 if numeric > 1e11 else numeric
    if isinstance(raw_value, str):
        try:
            dt = datetime.fromisoformat(raw_value)
        except ValueError as exc:
            raise VisualizationError("timestamp string must be ISO 8601 format") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    raise VisualizationError("timestamp must be int, float, or ISO 8601 string")


def _compute_drawdown_series(equity_series: Sequence[tuple[float, float]]) -> list[float]:
    peak = equity_series[0][1]
    drawdown_values: list[float] = []

    for _, equity in equity_series:
        if equity > peak:
            peak = equity
        if peak <= 0:
            drawdown_values.append(0.0)
        else:
            drawdown_values.append((peak - equity) / peak)

    return drawdown_values


def _extract_trade_pnls(trade_log: Sequence[Mapping[str, object]] | Sequence[object]) -> list[float]:
    pnls: list[float] = []
    for trade in trade_log:
        pnl = _extract_field(trade, "pnl_net")
        if pnl is None:
            pnl = _extract_field(trade, "pnl_gross")
        if pnl is None:
            continue
        if isinstance(pnl, (int, float)) and not isinstance(pnl, bool):
            pnls.append(float(pnl))
    return pnls


def _extract_holding_hours(
    trade_log: Sequence[Mapping[str, object]] | Sequence[object],
) -> list[float]:
    durations: list[float] = []
    for trade in trade_log:
        hold_seconds = _extract_field(trade, "holding_seconds")
        hold_minutes = _extract_field(trade, "holding_minutes")
        hold_hours = _extract_field(trade, "holding_hours")

        if isinstance(hold_seconds, (int, float)) and not isinstance(hold_seconds, bool):
            durations.append(float(hold_seconds) / 3600.0)
            continue
        if isinstance(hold_minutes, (int, float)) and not isinstance(hold_minutes, bool):
            durations.append(float(hold_minutes) / 60.0)
            continue
        if isinstance(hold_hours, (int, float)) and not isinstance(hold_hours, bool):
            durations.append(float(hold_hours))
            continue

        entry_time = _extract_field(trade, "entry_time")
        exit_time = _extract_field(trade, "exit_time")
        if entry_time is None or exit_time is None:
            continue

        try:
            entry_ts = _parse_timestamp(entry_time)
            exit_ts = _parse_timestamp(exit_time)
        except VisualizationError:
            continue
        if exit_ts > entry_ts:
            durations.append((exit_ts - entry_ts) / 3600.0)

    return durations


def _extract_field(trade: Mapping[str, object] | object, field_name: str) -> object | None:
    if isinstance(trade, Mapping):
        return trade.get(field_name)
    if hasattr(trade, field_name):
        return getattr(trade, field_name)
    return None
