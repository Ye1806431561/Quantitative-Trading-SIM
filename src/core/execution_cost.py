"""Execution-cost model for slippage and maker/taker fees."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from src.core.enums import OrderSide


class LiquidityRole(str, Enum):
    """Liquidity role used for fee-rate selection."""

    MAKER = "maker"
    TAKER = "taker"


@dataclass(frozen=True)
class ExecutionCostProfile:
    """Configurable rates for slippage and trading fees."""

    maker_fee_rate: float = 0.001
    taker_fee_rate: float = 0.001
    slippage_rate: float = 0.0005

    def __post_init__(self) -> None:
        self._validate_rate("maker_fee_rate", self.maker_fee_rate)
        self._validate_rate("taker_fee_rate", self.taker_fee_rate)
        self._validate_rate("slippage_rate", self.slippage_rate)

    def apply_slippage(self, *, reference_price: float, side: OrderSide) -> float:
        """Apply side-aware adverse slippage to reference execution price."""
        if reference_price <= 0:
            raise ValueError("reference_price must be > 0")

        if side == OrderSide.BUY:
            execution_price = reference_price * (1.0 + self.slippage_rate)
        else:
            execution_price = reference_price * (1.0 - self.slippage_rate)

        if execution_price <= 0:
            raise ValueError("execution_price must be > 0 after slippage")
        return execution_price

    def apply_slippage_with_limit(
        self,
        *,
        reference_price: float,
        side: OrderSide,
        limit_price: float,
    ) -> float:
        """Apply slippage but do not violate a resting limit-order price bound."""
        if limit_price <= 0:
            raise ValueError("limit_price must be > 0")

        slipped_price = self.apply_slippage(reference_price=reference_price, side=side)
        if side == OrderSide.BUY:
            return min(limit_price, slipped_price)
        return max(limit_price, slipped_price)

    def calculate_fee(self, *, execution_price: float, amount: float, liquidity: LiquidityRole) -> float:
        """Calculate absolute fee from notional and fee-rate by liquidity role."""
        if execution_price <= 0:
            raise ValueError("execution_price must be > 0")
        if amount <= 0:
            raise ValueError("amount must be > 0")
        return execution_price * amount * self.fee_rate(liquidity)

    def fee_rate(self, liquidity: LiquidityRole) -> float:
        if liquidity == LiquidityRole.MAKER:
            return self.maker_fee_rate
        return self.taker_fee_rate

    @staticmethod
    def _validate_rate(name: str, rate: float) -> None:
        if not isinstance(rate, (int, float)) or isinstance(rate, bool):
            raise ValueError(f"{name} must be numeric")
        numeric = float(rate)
        if numeric < 0 or numeric > 1:
            raise ValueError(f"{name} must be in range [0, 1]")
