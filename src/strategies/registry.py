"""Strategy registry for name/class lookup and allowed params."""

from __future__ import annotations

from dataclasses import dataclass

import backtrader as bt

from src.strategies.bollinger_strategy import BollingerStrategy
from src.strategies.grid_strategy import GridStrategy
from src.strategies.sma_strategy import SMAStrategy
from src.utils.config_defaults import DEFAULT_STRATEGIES_CONFIG


class StrategyParamError(ValueError):
    """Raised when strategy lookup or parameters are invalid."""


@dataclass(frozen=True)
class StrategySpec:
    name: str
    strategy_class: type[bt.Strategy]
    allowed_params: tuple[str, ...]


class StrategyRegistry:
    def __init__(self, specs: dict[str, StrategySpec]) -> None:
        self._by_name = dict(specs)
        self._by_class = {spec.strategy_class: spec for spec in specs.values()}

    @classmethod
    def default(cls) -> "StrategyRegistry":
        defaults = DEFAULT_STRATEGIES_CONFIG
        specs = {
            "sma_strategy": StrategySpec(
                name="sma_strategy",
                strategy_class=SMAStrategy,
                allowed_params=tuple(defaults["sma_strategy"]["params"].keys()),
            ),
            "grid_strategy": StrategySpec(
                name="grid_strategy",
                strategy_class=GridStrategy,
                allowed_params=tuple(defaults["grid_strategy"]["params"].keys()),
            ),
            "bollinger_strategy": StrategySpec(
                name="bollinger_strategy",
                strategy_class=BollingerStrategy,
                allowed_params=tuple(defaults["bollinger_strategy"]["params"].keys()),
            ),
        }
        return cls(specs)

    def get_by_name(self, name: str) -> StrategySpec:
        if name not in self._by_name:
            raise StrategyParamError(f"Unknown strategy name: {name}")
        return self._by_name[name]

    def get_by_class(self, strategy_class: type[bt.Strategy]) -> StrategySpec:
        if strategy_class not in self._by_class:
            raise StrategyParamError("Unknown strategy class")
        return self._by_class[strategy_class]
