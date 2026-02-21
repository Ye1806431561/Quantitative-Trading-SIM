"""Performance analysis module tests (Phase 4 Step 35)."""

import pytest

from src.analysis.performance import analyze_performance


def test_equity_curve_basic_metrics() -> None:
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1100.0,
        "2026-02-22T00:00:00": 1050.0,
        "2026-02-23T00:00:00": 1200.0,
    }

    summary = analyze_performance(equity_curve=equity, trade_log=[])

    assert summary.total_return == pytest.approx(0.2)
    assert summary.max_drawdown == pytest.approx((1100.0 - 1050.0) / 1100.0)
