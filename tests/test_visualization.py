"""Visualization module tests (Phase 4 Step 36)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.analysis.visualization import (
    PerformanceVisualizer,
    VisualizationError,
    _compute_drawdown_series,
)


@dataclass
class _TradeObject:
    entry_time: str
    exit_time: str
    pnl_net: float


def _sample_equity_curve() -> dict[str, float]:
    return {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1100.0,
        "2026-02-22T00:00:00": 1045.0,
        "2026-02-23T00:00:00": 1200.0,
    }


def _sample_trade_log() -> list[object]:
    return [
        {
            "entry_time": "2026-02-20T00:00:00",
            "exit_time": "2026-02-20T06:00:00",
            "pnl_net": 35.0,
            "holding_minutes": 360.0,
        },
        {
            "entry_time": "2026-02-21T00:00:00",
            "exit_time": "2026-02-21T04:00:00",
            "pnl_net": -20.0,
            "holding_seconds": 4 * 3600,
        },
        _TradeObject(
            entry_time="2026-02-22T00:00:00",
            exit_time="2026-02-22T08:00:00",
            pnl_net=18.0,
        ),
    ]


def test_export_all_creates_four_images(tmp_path: Path) -> None:
    output_dir = tmp_path / "plots"
    visualizer = PerformanceVisualizer(output_dir)

    artifacts = visualizer.export_all(
        equity_curve=_sample_equity_curve(),
        trade_log=_sample_trade_log(),
        prefix="BTC_1h",
    )

    assert artifacts.equity_curve_path.name == "equity_curve_BTC_1h.png"
    assert artifacts.drawdown_curve_path.name == "drawdown_curve_BTC_1h.png"
    assert artifacts.trade_distribution_path.name == "trade_distribution_BTC_1h.png"
    assert artifacts.holding_time_path.name == "holding_time_BTC_1h.png"

    for output_path in (
        artifacts.equity_curve_path,
        artifacts.drawdown_curve_path,
        artifacts.trade_distribution_path,
        artifacts.holding_time_path,
    ):
        assert output_path.exists()
        assert output_path.stat().st_size > 0


def test_export_all_handles_empty_trade_log(tmp_path: Path) -> None:
    visualizer = PerformanceVisualizer(tmp_path)

    artifacts = visualizer.export_all(equity_curve=_sample_equity_curve(), trade_log=[])

    assert artifacts.trade_distribution_path.exists()
    assert artifacts.holding_time_path.exists()
    assert artifacts.trade_distribution_path.stat().st_size > 0
    assert artifacts.holding_time_path.stat().st_size > 0


def test_drawdown_series_matches_expected_values() -> None:
    equity_series = [
        (1.0, 100.0),
        (2.0, 110.0),
        (3.0, 99.0),
        (4.0, 120.0),
        (5.0, 90.0),
    ]

    drawdown = _compute_drawdown_series(equity_series)

    assert drawdown == pytest.approx([0.0, 0.0, 0.1, 0.0, 0.25])


def test_export_all_rejects_invalid_equity_curve(tmp_path: Path) -> None:
    visualizer = PerformanceVisualizer(tmp_path)

    with pytest.raises(VisualizationError, match="at least two points"):
        visualizer.export_all(
            equity_curve={"2026-02-20T00:00:00": 1000.0},
            trade_log=_sample_trade_log(),
        )


def test_export_all_accepts_datetime_timestamps(tmp_path: Path) -> None:
    visualizer = PerformanceVisualizer(tmp_path)
    equity_curve = {
        datetime(2026, 2, 20, tzinfo=timezone.utc): 1000.0,
        datetime(2026, 2, 21): 1100.0,
    }
    trade_log = [
        {
            "entry_time": datetime(2026, 2, 20, 0, 0),
            "exit_time": datetime(2026, 2, 20, 6, 0, tzinfo=timezone.utc),
            "pnl_net": 12.5,
        }
    ]

    artifacts = visualizer.export_all(equity_curve=equity_curve, trade_log=trade_log)

    assert artifacts.equity_curve_path.exists()
    assert artifacts.holding_time_path.exists()
    assert artifacts.equity_curve_path.stat().st_size > 0
    assert artifacts.holding_time_path.stat().st_size > 0
