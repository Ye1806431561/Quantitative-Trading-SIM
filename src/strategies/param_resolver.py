"""Resolve strategy parameters from config + explicit overrides."""

from __future__ import annotations

from typing import Any, Mapping

from src.strategies.registry import StrategyParamError, StrategyRegistry


class StrategyParamResolver:
    def __init__(self, strategies_config: Mapping[str, Any], registry: StrategyRegistry) -> None:
        self._config = strategies_config
        self._registry = registry

    def resolve_for_name(
        self,
        name: str,
        explicit_params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._registry.get_by_name(name)
        config_entry = self._config.get(name)
        if not isinstance(config_entry, Mapping):
            raise StrategyParamError(f"Missing strategy config: {name}")
        if not config_entry.get("enabled", False):
            raise StrategyParamError(f"Strategy disabled: {name}")

        config_params = dict(config_entry.get("params", {}))
        merged = dict(config_params)
        if explicit_params:
            merged.update(explicit_params)
            
        unknown = set(merged.keys()) - set(spec.allowed_params)
        if unknown:
            raise StrategyParamError(f"unknown parameter(s): {sorted(unknown)}")
            
        return merged

    def resolve_for_class(
        self,
        strategy_class: type,
        explicit_params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        spec = self._registry.get_by_class(strategy_class)
        return self.resolve_for_name(spec.name, explicit_params)


__all__ = ["StrategyParamResolver", "StrategyParamError"]
