# Performance Analysis Module Design

**Date:** 2026-02-21

## Goal
Build a reusable performance analysis module that works for both backtest and live runs, using equity curves and trade logs to compute core metrics (total return, annualized return, max drawdown, Sharpe, Sortino, win rate, profit factor).

## Scope
- Inputs: equity curve and/or returns series, plus trade logs
- Outputs: a summary metrics object (serializable and testable)
- No visualization in this step (reserved for Step 36)

## Inputs
### Equity Curve (Preferred)
- Format: `dict[timestamp, equity]` or sequence of `(timestamp, equity)`
- Timestamp formats supported:
  - ISO 8601 string
  - Millisecond integer

### Returns Series (Fallback)
- Format: `dict[timestamp, return]` or sequence of `(timestamp, return)`
- Requires `initial_capital` to reconstruct equity curve

### Trade Log
- Sequence of trades containing at least `pnl_net` or `pnl_gross`
- For this step we focus on win rate and profit factor

## Input Resolution Rules
- If both `equity_curve` and `returns_series` are provided, use `equity_curve`
- If only `returns_series` is provided, reconstruct equity from `initial_capital`
- If neither is provided, raise a validation error

## Metrics
- **Total Return:** `(final_equity / initial_equity) - 1`
- **Annualized Return:** `(final / initial)^(year_seconds / elapsed_seconds) - 1`
- **Max Drawdown:** `max((peak - trough) / peak)` computed over equity curve
- **Sharpe Ratio:** `mean(excess_returns) / std(returns) * sqrt(annualization_factor)`
- **Sortino Ratio:** `mean(excess_returns) / std(negative_returns) * sqrt(annualization_factor)`
- **Win Rate:** `winning_trades / total_trades`
- **Profit Factor:** `gross_profit / gross_loss` (None if no losses and gross_profit > 0)

## Edge Handling
- Empty or insufficient samples: Sharpe/Sortino return `None`
- Zero variance returns: Sharpe/Sortino return `None`
- No trades: win rate `0.0`, profit factor `0.0`
- All winning trades: profit factor `None`

## API Sketch
- Module: `src/analysis/performance.py`
- Entry point: `analyze_performance(...) -> PerformanceSummary`

## Tests
- New test file: `tests/test_performance_analysis.py`
- Hand-calculated fixtures for:
  - total return, annualized return, max drawdown
  - Sharpe/Sortino edge cases (zero variance, no downside)
  - win rate/profit factor edge cases (no trades, all wins, mixed)

## Integration Notes
- Backtest: reuse `time_series_returns` and `trade_log` from `BacktestRunResult`
- Live: feed equity snapshots + live trade log

