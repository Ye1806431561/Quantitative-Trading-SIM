from __future__ import annotations

import pytest

from src.strategies.param_resolver import StrategyParamResolver, StrategyParamError
from src.strategies.registry import StrategyRegistry


def _base_config() -> dict:
    return {
        "sma_strategy": {
            "enabled": True,
            "params": {"fast_period": 10, "slow_period": 30, "position_size": 0.2},
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


def test_resolver_merges_config_and_explicit_params():
    config = _base_config()
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    params = resolver.resolve_for_name(
        "sma_strategy",
        {"fast_period": 5},
    )

    assert params["fast_period"] == 5
    assert params["slow_period"] == 30
    assert params["position_size"] == 0.2


def test_resolver_rejects_unknown_param():
    config = _base_config()
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    with pytest.raises(StrategyParamError, match="unknown parameter"):
        resolver.resolve_for_name("sma_strategy", {"unknown": 1})


def test_resolver_rejects_disabled_strategy():
    config = _base_config()
    config["grid_strategy"]["enabled"] = False
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    with pytest.raises(StrategyParamError, match="disabled"):
        resolver.resolve_for_name("grid_strategy", {})


def test_resolver_rejects_unknown_param_in_config():
    config = _base_config()
    config["sma_strategy"]["params"]["unknown"] = 1
    registry = StrategyRegistry.default()
    resolver = StrategyParamResolver(config, registry)

    with pytest.raises(StrategyParamError, match="unknown parameter"):
        resolver.resolve_for_name("sma_strategy")
