"""Factory for building live strategies from config."""

from __future__ import annotations

from typing import Any, Mapping

from src.strategies.adapter import BacktraderAdapter
from src.strategies.base import LiveStrategy
from src.strategies.param_resolver import StrategyParamResolver
from src.strategies.registry import StrategyRegistry


def create_live_strategy(
    strategy_name: str,
    strategies_config: Mapping[str, Any],
    explicit_params: Mapping[str, Any] | None = None,
    *,
    registry: StrategyRegistry | None = None,
) -> tuple[LiveStrategy, dict[str, Any]]:
    registry = registry or StrategyRegistry.default()
    resolver = StrategyParamResolver(strategies_config, registry)
    params = resolver.resolve_for_name(strategy_name, explicit_params)
    spec = registry.get_by_name(strategy_name)

    position_size = float(params.get("position_size", 0.1))
    bt_params = {key: value for key, value in params.items() if key != "position_size"}

    adapter = BacktraderAdapter(
        name=strategy_name,
        bt_strategy_cls=spec.strategy_class,
        bt_params=bt_params,
        position_size=position_size,
    )
    return adapter, params
