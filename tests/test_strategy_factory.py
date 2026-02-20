from __future__ import annotations

from src.strategies.adapter import BacktraderAdapter
from src.strategies.factory import create_live_strategy


def test_factory_builds_adapter_with_config_params():
    config = {
        "sma_strategy": {
            "enabled": True,
            "params": {"fast_period": 5, "slow_period": 9, "position_size": 0.3},
        },
        "grid_strategy": {
            "enabled": True,
            "params": {"grid_num": 10, "price_range": 0.1, "position_size": 0.1},
        },
        "bollinger_strategy": {
            "enabled": True,
            "params": {"period": 20, "dev": 2.0, "position_size": 0.2},
        },
    }

    strategy, params = create_live_strategy("sma_strategy", config, explicit_params=None)

    assert isinstance(strategy, BacktraderAdapter)
    assert strategy._bt_params["fast_period"] == 5
    assert strategy._bt_params["slow_period"] == 9
    assert strategy._position_size == 0.3
    assert params["position_size"] == 0.3
