"""Performance analysis module tests (Phase 4 Step 35)."""

from datetime import datetime, timezone

import pytest

from src.analysis.performance import PerformanceAnalysisError, analyze_performance


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
        period_seconds=86400.0,
        trade_log=[],
    )

    assert summary.total_return == pytest.approx(0.025049, rel=1e-6)
    
    # 投资期总共为 3 天（T0 = 02-19, T3 = 02-22）
    expected_annualized = (1.025049) ** (365 / 3) - 1.0
    assert summary.annualized_return == pytest.approx(expected_annualized, rel=1e-6)
    
    # Sharpe Ratio 计算基准：
    import statistics
    import math
    rets = [0.01, -0.005, 0.02]
    expected_sharpe = statistics.mean(rets) / statistics.pstdev(rets) * math.sqrt(365.0)
    assert summary.sharpe_ratio == pytest.approx(expected_sharpe, rel=1e-6)


def test_returns_series_requires_period_seconds() -> None:
    returns = {
        "2026-02-20T00:00:00": 0.01,
        "2026-02-21T00:00:00": -0.005,
    }

    with pytest.raises(
        PerformanceAnalysisError,
        match="period_seconds is required when using returns_series",
    ):
        analyze_performance(
            returns_series=returns,
            initial_capital=1000.0,
            trade_log=[],
        )


def test_returns_series_interval_must_match_period_seconds() -> None:
    returns = {
        "2026-02-20T00:00:00": 0.01,
        "2026-02-21T00:00:00": -0.005,
        "2026-02-23T00:00:00": 0.02,
    }

    with pytest.raises(
        PerformanceAnalysisError,
        match="returns_series timestamp interval must match period_seconds",
    ):
        analyze_performance(
            returns_series=returns,
            initial_capital=1000.0,
            period_seconds=86400.0,
            trade_log=[],
        )



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


def test_returns_series_accepts_datetime_timestamps() -> None:
    returns = {
        datetime(2026, 2, 20, tzinfo=timezone.utc): 0.01,
        datetime(2026, 2, 21): -0.005,
        datetime(2026, 2, 22, tzinfo=timezone.utc): 0.02,
    }

    summary = analyze_performance(
        returns_series=returns,
        initial_capital=1000.0,
        period_seconds=86400.0,
        trade_log=[],
    )

    assert summary.total_return == pytest.approx(0.025049, rel=1e-6)
