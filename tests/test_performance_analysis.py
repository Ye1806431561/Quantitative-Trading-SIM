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


def test_returns_series_reconstructs_equity() -> None:
    returns = {
        "2026-02-20T00:00:00": 0.01,
        "2026-02-21T00:00:00": -0.005,
        "2026-02-22T00:00:00": 0.02,
    }

    summary = analyze_performance(
        returns_series=returns,
        initial_capital=1000.0,
        trade_log=[],
    )

    assert summary.total_return == pytest.approx(0.025049, rel=1e-6)



def test_sharpe_and_sortino_none_when_zero_variance() -> None:
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1010.0,
        "2026-02-22T00:00:00": 1020.1,
    }

    summary = analyze_performance(equity_curve=equity, trade_log=[])

    assert summary.sharpe_ratio is None
    assert summary.sortino_ratio is None


def test_trade_log_metrics() -> None:
    equity = {
        "2026-02-20T00:00:00": 1000.0,
        "2026-02-21T00:00:00": 1100.0,
    }
    trade_log = [
        {"pnl_net": 10.0},
        {"pnl_net": -5.0},
        {"pnl_net": 20.0},
    ]

    summary = analyze_performance(equity_curve=equity, trade_log=trade_log)

    assert summary.total_trades == 3
    assert summary.winning_trades == 2
    assert summary.losing_trades == 1
    assert summary.win_rate == pytest.approx(2 / 3)
    assert summary.profit_factor == pytest.approx(30.0 / 5.0)
