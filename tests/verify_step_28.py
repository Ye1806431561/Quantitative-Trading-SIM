"""Demo script for step 28: backtest result export verification."""

from pathlib import Path

from src.backtest.exporter import BacktestResultExporter
from src.backtest.result_models import (
    BacktestRunResult,
    ReturnsAnalysis,
    RiskMetrics,
    TradeStatistics,
)


def create_sample_result() -> BacktestRunResult:
    """Create a sample backtest result for demonstration."""
    return BacktestRunResult(
        symbol="BTC/USDT",
        timeframe="1h",
        data_source="sqlite",
        initial_capital=10000.0,
        final_value=12500.0,
        pnl=2500.0,
        total_return_pct=25.0,
        bars_processed=720,
        trade_stats=TradeStatistics(
            total_trades=10,
            won_trades=7,
            lost_trades=3,
            win_rate=70.0,
            profit_factor=2.5,
            avg_profit=500.0,
            avg_loss=-200.0,
            max_profit=1000.0,
            max_loss=-400.0,
        ),
        risk_metrics=RiskMetrics(
            sharpe_ratio=1.8,
            max_drawdown_pct=15.5,
            max_drawdown_duration_days=7,
        ),
        returns_analysis=ReturnsAnalysis(
            total_return=0.25,
            avg_return=0.0035,
        ),
        time_series_returns={
            "2024-01-01T00:00:00": 0.0,
            "2024-01-02T00:00:00": 0.02,
            "2024-01-03T00:00:00": 0.05,
            "2024-01-04T00:00:00": 0.03,
            "2024-01-05T00:00:00": 0.08,
            "2024-01-06T00:00:00": 0.12,
            "2024-01-07T00:00:00": 0.15,
            "2024-01-08T00:00:00": 0.18,
            "2024-01-09T00:00:00": 0.22,
            "2024-01-10T00:00:00": 0.25,
        },
    )


def main() -> None:
    """Demonstrate backtest result export functionality."""
    print("=" * 60)
    print("Step 28 Verification: Backtest Result Export")
    print("=" * 60)
    
    # Create output directory
    output_dir = Path("data") / "backtest_results"
    print(f"\n1. Creating output directory: {output_dir}")
    
    # Initialize exporter
    exporter = BacktestResultExporter(output_dir)
    print("   ✓ Exporter initialized")
    
    # Create sample result
    print("\n2. Creating sample backtest result...")
    result = create_sample_result()
    print(f"   ✓ Symbol: {result.symbol}")
    print(f"   ✓ Timeframe: {result.timeframe}")
    print(f"   ✓ Initial Capital: ${result.initial_capital:,.2f}")
    print(f"   ✓ Final Value: ${result.final_value:,.2f}")
    print(f"   ✓ PnL: ${result.pnl:,.2f} ({result.total_return_pct:.2f}%)")
    print(f"   ✓ Total Trades: {result.trade_stats.total_trades}")
    print(f"   ✓ Win Rate: {result.trade_stats.win_rate:.1f}%")
    print(f"   ✓ Sharpe Ratio: {result.risk_metrics.sharpe_ratio}")
    
    # Export all formats
    print("\n3. Exporting results...")
    paths = exporter.export_all(result, prefix="demo")
    
    print("\n4. Export completed successfully!")
    print("\n   Generated files:")
    for file_type, path in paths.items():
        file_size = path.stat().st_size
        print(f"   ✓ {file_type:15s}: {path.name:30s} ({file_size:,} bytes)")
    
    print("\n5. Verification:")
    print(f"   ✓ All 4 files exist: {all(p.exists() for p in paths.values())}")
    print(f"   ✓ Output directory: {output_dir.absolute()}")
    
    print("\n" + "=" * 60)
    print("Step 28 verification completed successfully!")
    print("=" * 60)
    print("\nYou can now:")
    print(f"  - View JSON files: cat {output_dir}/backtest_summary_demo.json")
    print(f"  - View CSV files: cat {output_dir}/backtest_summary_demo.csv")
    print(f"  - Open in Excel: open {output_dir}/backtest_summary_demo.csv")
    print()


if __name__ == "__main__":
    main()

