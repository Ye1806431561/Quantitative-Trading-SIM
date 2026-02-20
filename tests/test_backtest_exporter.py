"""Tests for backtest result exporter (step 28)."""

import csv
import json
from pathlib import Path

import pytest

from src.backtest.exporter import BacktestExporterError, BacktestResultExporter
from src.backtest.result_models import (
    BacktestRunResult,
    ReturnsAnalysis,
    RiskMetrics,
    TradeStatistics,
)


@pytest.fixture
def sample_result() -> BacktestRunResult:
    """Create a sample backtest result for testing."""
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
        },
    )


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory."""
    output_dir = tmp_path / "backtest_results"
    output_dir.mkdir()
    return output_dir


def test_export_summary_json_creates_file(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that summary JSON export creates a valid file."""
    exporter = BacktestResultExporter(temp_output_dir)
    output_path = exporter.export_summary_json(sample_result)
    
    assert output_path.exists()
    assert output_path.suffix == ".json"
    
    # Verify JSON structure
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    
    assert "basic_info" in data
    assert "capital" in data
    assert "trade_statistics" in data
    assert "risk_metrics" in data
    assert "returns_analysis" in data
    
    # Verify key fields
    assert data["basic_info"]["symbol"] == "BTC/USDT"
    assert data["capital"]["initial_capital"] == 10000.0
    assert data["capital"]["final_value"] == 12500.0
    assert data["trade_statistics"]["total_trades"] == 10
    assert data["risk_metrics"]["sharpe_ratio"] == 1.8


def test_export_summary_csv_creates_file(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that summary CSV export creates a valid file with flattened structure."""
    exporter = BacktestResultExporter(temp_output_dir)
    output_path = exporter.export_summary_csv(sample_result)
    
    assert output_path.exists()
    assert output_path.suffix == ".csv"
    
    # Verify CSV structure
    with open(output_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    assert len(rows) > 1  # Header + data rows
    assert rows[0] == ["Metric", "Value"]
    
    # Convert to dict for easier verification
    data_dict = {row[0]: row[1] for row in rows[1:]}
    
    # Verify flattened keys exist
    assert "basic_info.symbol" in data_dict
    assert "capital.initial_capital" in data_dict
    assert "trade_statistics.total_trades" in data_dict
    assert "risk_metrics.sharpe_ratio" in data_dict
    
    # Verify values
    assert data_dict["basic_info.symbol"] == "BTC/USDT"
    assert float(data_dict["capital.pnl"]) == 2500.0


def test_export_equity_curve_json_creates_file(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that equity curve JSON export creates a valid file."""
    exporter = BacktestResultExporter(temp_output_dir)
    output_path = exporter.export_equity_curve_json(sample_result)
    
    assert output_path.exists()
    assert output_path.suffix == ".json"
    
    # Verify JSON structure
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    
    assert "symbol" in data
    assert "timeframe" in data
    assert "initial_capital" in data
    assert "time_series" in data
    
    # Verify time series data
    assert len(data["time_series"]) == 5
    assert "2024-01-01T00:00:00" in data["time_series"]
    assert data["time_series"]["2024-01-05T00:00:00"] == 0.08


def test_export_equity_curve_csv_creates_file(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that equity curve CSV export creates a valid file."""
    exporter = BacktestResultExporter(temp_output_dir)
    output_path = exporter.export_equity_curve_csv(sample_result)
    
    assert output_path.exists()
    assert output_path.suffix == ".csv"
    
    # Verify CSV structure
    with open(output_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    assert len(rows) == 6  # Header + 5 data rows
    assert rows[0] == ["Timestamp", "Return"]
    
    # Verify data is sorted by timestamp
    timestamps = [row[0] for row in rows[1:]]
    assert timestamps == sorted(timestamps)
    
    # Verify values
    assert rows[1][0] == "2024-01-01T00:00:00"
    assert float(rows[1][1]) == 0.0
    assert float(rows[-1][1]) == 0.08


def test_export_all_creates_all_files(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that export_all creates all six output files (step 28)."""
    exporter = BacktestResultExporter(temp_output_dir)
    paths = exporter.export_all(sample_result)

    assert len(paths) == 6
    assert "summary_json" in paths
    assert "summary_csv" in paths
    assert "equity_json" in paths
    assert "equity_csv" in paths
    assert "trade_log_json" in paths
    assert "trade_log_csv" in paths

    # Verify all files exist
    for path in paths.values():
        assert path.exists()


def test_export_all_with_prefix(
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that export_all with prefix creates correctly named files."""
    exporter = BacktestResultExporter(temp_output_dir)
    paths = exporter.export_all(sample_result, prefix="BTC_1h")

    # Verify filenames contain prefix
    assert paths["summary_json"].name == "backtest_summary_BTC_1h.json"
    assert paths["summary_csv"].name == "backtest_summary_BTC_1h.csv"
    assert paths["equity_json"].name == "equity_curve_BTC_1h.json"
    assert paths["equity_csv"].name == "equity_curve_BTC_1h.csv"
    assert paths["trade_log_json"].name == "trade_log_BTC_1h.json"
    assert paths["trade_log_csv"].name == "trade_log_BTC_1h.csv"


def test_exporter_creates_output_directory_if_missing(tmp_path: Path) -> None:
    """Test that exporter creates output directory if it doesn't exist."""
    output_dir = tmp_path / "nested" / "output" / "dir"
    assert not output_dir.exists()
    
    exporter = BacktestResultExporter(output_dir)
    assert output_dir.exists()


def test_export_handles_none_values_in_result(temp_output_dir: Path) -> None:
    """Test that exporter handles None values gracefully (e.g., sharpe_ratio=None)."""
    result_with_none = BacktestRunResult(
        symbol="ETH/USDT",
        timeframe="4h",
        data_source="sqlite",
        initial_capital=5000.0,
        final_value=5100.0,
        pnl=100.0,
        total_return_pct=2.0,
        bars_processed=100,
        trade_stats=TradeStatistics(
            total_trades=0,
            won_trades=0,
            lost_trades=0,
            win_rate=0.0,
            profit_factor=None,  # None when no losing trades
            avg_profit=0.0,
            avg_loss=0.0,
            max_profit=0.0,
            max_loss=0.0,
        ),
        risk_metrics=RiskMetrics(
            sharpe_ratio=None,  # None when insufficient data
            max_drawdown_pct=0.0,
            max_drawdown_duration_days=0,
        ),
        returns_analysis=ReturnsAnalysis(
            total_return=0.02,
            avg_return=0.0002,
        ),
        time_series_returns={},
    )
    
    exporter = BacktestResultExporter(temp_output_dir)
    
    # Should not raise exception
    json_path = exporter.export_summary_json(result_with_none)
    csv_path = exporter.export_summary_csv(result_with_none)
    
    assert json_path.exists()
    assert csv_path.exists()
    
    # Verify None is properly serialized in JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["risk_metrics"]["sharpe_ratio"] is None
    assert data["trade_statistics"]["profit_factor"] is None

    # Verify None is serialized as 'None' string in CSV (not empty string)
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    data_dict = {row[0]: row[1] for row in rows[1:]}
    assert data_dict["risk_metrics.sharpe_ratio"] == "None"
    assert data_dict["trade_statistics.profit_factor"] == "None"


def test_export_trade_log_json(
    temp_output_dir: Path,
) -> None:
    """Test trade log JSON export with actual trade records (step 28)."""
    import tempfile, os
    from src.core.database import SQLiteDatabase
    from src.backtest.engine import BacktestEngine, BacktestRunRequest
    from tests.test_backtest_analyzers import SimpleTestStrategy

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    db = SQLiteDatabase(db_path)
    db.initialize_schema()
    base_ts = 1609459200000
    with db.transaction() as tx:
        for i in range(30):
            ts = base_ts + i * 3600000
            op = 40000.0 + i * 100
            tx.execute(
                "INSERT INTO candles(symbol,timeframe,timestamp,open,high,low,close,volume) "
                "VALUES(?,?,?,?,?,?,?,?)",
                ("BTC/USDT", "1h", ts, op, op + 200, op - 100, op + 150, 10.0),
            )
    engine = BacktestEngine(db, initial_capital=10000.0, commission_rate=0.001, slippage_rate=0.0)
    req = BacktestRunRequest(
        symbol="BTC/USDT", timeframe="1h",
        start_timestamp=base_ts, end_timestamp=base_ts + 29 * 3600000,
        strategy_class=SimpleTestStrategy,
    )
    result = engine.run(req)
    db.close()
    os.unlink(db_path)

    # Verify trade_log has actual records
    assert len(result.trade_log) > 0, "SimpleTestStrategy must produce closed trades"

    exporter = BacktestResultExporter(temp_output_dir)
    json_path = exporter.export_trade_log_json(result)
    csv_path = exporter.export_trade_log_csv(result)

    assert json_path.exists()
    assert csv_path.exists()

    # Verify JSON structure
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["symbol"] == "BTC/USDT"
    assert data["total_trades"] == len(result.trade_log)
    assert len(data["trades"]) == len(result.trade_log)
    first = data["trades"][0]
    assert "entry_time" in first
    assert "exit_time" in first
    assert "side" in first
    assert "pnl_net" in first
    assert first["side"] == "long"

    # Verify CSV rows
    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["entry_time", "exit_time", "side", "size",
                       "entry_price", "exit_price", "pnl_gross", "pnl_net"]
    assert len(rows) == len(result.trade_log) + 1  # header + data rows


@pytest.mark.parametrize(
    "method_name",
    [
        "export_summary_json",
        "export_summary_csv",
        "export_equity_curve_json",
        "export_equity_curve_csv",
        "export_trade_log_json",
        "export_trade_log_csv",
    ],
)
def test_export_methods_handle_os_error(
    method_name: str,
    sample_result: BacktestRunResult,
    tmp_path: Path,
) -> None:
    """Test that all export methods raise BacktestExporterError on write failure (OSError)."""
    import stat

    output_dir = tmp_path / "readonly_dir"
    output_dir.mkdir()
    output_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)  # read+exec only, no write

    # Bypass __init__ mkdir matching permission error
    exporter = BacktestResultExporter.__new__(BacktestResultExporter)
    exporter._output_dir = output_dir

    try:
        method = getattr(exporter, method_name)
        with pytest.raises(BacktestExporterError, match="Failed to export.*"):
            method(sample_result)
    finally:
        output_dir.chmod(stat.S_IRWXU)  # restore permissions for cleanup


@pytest.mark.parametrize(
    "method_name",
    [
        "export_summary_json",
        "export_equity_curve_json",
        "export_trade_log_json",
    ],
)
def test_export_methods_handle_type_error(
    method_name: str,
    sample_result: BacktestRunResult,
    temp_output_dir: Path,
) -> None:
    """Test that JSON export methods raise BacktestExporterError on serialization failure (TypeError)."""
    from dataclasses import replace

    # Inject a non-serializable object into a field likely to be serialized
    # For summary: inject into basic_info via symbol (though symbol is str, we fit object)
    # For equity curve: inject into time_series_returns values
    # For trade log: inject into trade_log records

    class NonSerializable:
        pass

    bad_obj = NonSerializable()

    # Create a compromised result object based on the method being tested
    if method_name == "export_summary_json":
        # Inject into trade_stats (nested dict)
        # We can't easily break dataclass type safety, so we mock the entire structure behavior
        # checking _build_summary_dict -> asdict
        # Instead, let's inject into the dynamic aggregation dict in exporter?
        # No, exporter pulls from dataclass. We must make dataclass hold bad data.
        # Python run-time allows type violation.
        bad_stats = replace(sample_result.trade_stats, max_profit=bad_obj)  # type: ignore
        compromised_result = replace(sample_result, trade_stats=bad_stats)
    
    elif method_name == "export_equity_curve_json":
        # Inject into time_series_returns dict
        bad_series = {"2024-01-01": bad_obj}  # type: ignore
        compromised_result = replace(sample_result, time_series_returns=bad_series)
        
    elif method_name == "export_trade_log_json":
        # Inject into trade_log tuple
        # We need a TradeRecord with a bad field
        from src.backtest.result_models import TradeRecord
        bad_record = TradeRecord(
            entry_time="2024-01-01",
            exit_time="2024-01-02",
            side="long",
            size=1.0,
            entry_price=bad_obj,  # type: ignore
            exit_price=100.0,
            pnl_gross=10.0,
            pnl_net=9.0,
        )
        compromised_result = replace(sample_result, trade_log=(bad_record,))
        
    else:
        compromised_result = sample_result

    exporter = BacktestResultExporter(temp_output_dir)
    method = getattr(exporter, method_name)
    
    with pytest.raises(BacktestExporterError, match="Failed to export.*JSON.*"):
        method(compromised_result)




