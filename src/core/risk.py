"""Pre-order risk controls (Phase 2 Step 24)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from src.core.account_service import AccountService, AccountServiceError
from src.core.database import SQLiteDatabase
from src.core.enums import OrderSide
from src.utils.config_defaults import DEFAULT_CONFIG
from src.utils.logger import get_logger

_EPS = 1e-12


class RiskControlError(RuntimeError):
    """Raised when a risk rule blocks a new order."""


@dataclass(frozen=True)
class RiskLimits:
    """Configured risk-control thresholds."""

    max_position_size: float
    max_total_position: float
    max_drawdown: float

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> "RiskLimits":
        risk_cfg = config.get("risk")
        if not isinstance(risk_cfg, Mapping):
            raise RiskControlError("missing risk configuration")

        max_position_size = _as_positive_ratio(risk_cfg, "max_position_size")
        max_total_position = _as_positive_ratio(risk_cfg, "max_total_position")
        max_drawdown = _as_non_negative_ratio(risk_cfg, "max_drawdown")

        if max_position_size - max_total_position > _EPS:
            raise RiskControlError("risk.max_position_size must be <= risk.max_total_position")

        return cls(
            max_position_size=max_position_size,
            max_total_position=max_total_position,
            max_drawdown=max_drawdown,
        )


@dataclass(frozen=True)
class RiskCheckSnapshot:
    """Computed risk-state values at order-check time."""

    total_assets: float
    drawdown: float
    order_notional: float
    single_position_ratio: float
    projected_total_position_ratio: float


class RiskControl:
    """Evaluate single-order, total-position, and drawdown constraints."""

    def __init__(
        self,
        database: SQLiteDatabase,
        account_service: AccountService,
        limits: RiskLimits | None = None,
    ) -> None:
        self._db = database
        self._account_service = account_service
        self._limits = limits or RiskLimits.from_config(DEFAULT_CONFIG)
        self._peak_equity: float | None = None
        self._logger = get_logger("trade")

    def check_pre_order(
        self,
        *,
        symbol: str,
        side: OrderSide,
        amount: float,
        reference_price: float,
    ) -> RiskCheckSnapshot:
        normalized_symbol = symbol.strip()
        if not normalized_symbol:
            raise RiskControlError("symbol must not be empty")
        if amount <= 0:
            raise RiskControlError("amount must be > 0")
        if reference_price <= 0:
            raise RiskControlError("reference_price must be > 0")

        (
            base_cash,
            total_assets,
            current_positions_value,
            cost_basis_value,
        ) = self._portfolio_metrics({normalized_symbol: reference_price})

        if total_assets <= _EPS:
            self._reject(
                symbol=normalized_symbol,
                side=side,
                amount=amount,
                reference_price=reference_price,
                reason="insufficient total assets for risk evaluation",
            )

        peak_equity = self._update_peak_equity(
            total_assets=total_assets,
            base_cash=base_cash,
            cost_basis_value=cost_basis_value,
        )
        drawdown = _safe_ratio(peak_equity - total_assets, peak_equity)

        order_notional = amount * reference_price
        single_position_ratio = _safe_ratio(order_notional, total_assets)
        projected_total_position_ratio = _safe_ratio(
            current_positions_value + (order_notional if side == OrderSide.BUY else 0.0),
            total_assets,
        )

        if side == OrderSide.BUY and drawdown - self._limits.max_drawdown > _EPS:
            self._reject(
                symbol=normalized_symbol,
                side=side,
                amount=amount,
                reference_price=reference_price,
                reason=(
                    "max drawdown limit exceeded: "
                    f"{drawdown:.4f} > {self._limits.max_drawdown:.4f}"
                ),
            )

        if side == OrderSide.BUY and single_position_ratio - self._limits.max_position_size > _EPS:
            self._reject(
                symbol=normalized_symbol,
                side=side,
                amount=amount,
                reference_price=reference_price,
                reason=(
                    "single position limit exceeded: "
                    f"{single_position_ratio:.4f} > {self._limits.max_position_size:.4f}"
                ),
            )

        if side == OrderSide.BUY and projected_total_position_ratio - self._limits.max_total_position > _EPS:
            self._reject(
                symbol=normalized_symbol,
                side=side,
                amount=amount,
                reference_price=reference_price,
                reason=(
                    "total position limit exceeded: "
                    f"{projected_total_position_ratio:.4f} > {self._limits.max_total_position:.4f}"
                ),
            )

        return RiskCheckSnapshot(
            total_assets=total_assets,
            drawdown=drawdown,
            order_notional=order_notional,
            single_position_ratio=single_position_ratio,
            projected_total_position_ratio=projected_total_position_ratio,
        )

    def _portfolio_metrics(
        self,
        price_overrides: Mapping[str, float],
    ) -> tuple[float, float, float, float]:
        base_cash = self._read_base_cash()
        current_positions_value = 0.0
        cost_basis_value = 0.0

        with self._db.transaction() as tx:
            rows = tx.execute(
                """
                SELECT symbol, amount, entry_price, current_price
                FROM positions;
                """
            ).fetchall()

        for row in rows:
            amount = float(row["amount"])
            if amount <= _EPS:
                continue

            symbol = str(row["symbol"])
            entry_price = float(row["entry_price"])
            reference_price = _resolve_reference_price(
                symbol=symbol,
                entry_price=entry_price,
                current_price=row["current_price"],
                price_overrides=price_overrides,
            )
            current_positions_value += amount * reference_price
            cost_basis_value += amount * entry_price

        total_assets = base_cash + current_positions_value
        return base_cash, total_assets, current_positions_value, cost_basis_value

    def _read_base_cash(self) -> float:
        try:
            base_account = self._account_service.get_account(self._account_service.base_currency)
        except AccountServiceError:
            return 0.0
        return float(base_account.available + base_account.frozen)

    def _update_peak_equity(
        self,
        *,
        total_assets: float,
        base_cash: float,
        cost_basis_value: float,
    ) -> float:
        estimated_peak = max(total_assets, base_cash + cost_basis_value)
        if self._peak_equity is None:
            self._peak_equity = estimated_peak
        else:
            self._peak_equity = max(self._peak_equity, estimated_peak)
        return self._peak_equity

    def _reject(
        self,
        *,
        symbol: str,
        side: OrderSide,
        amount: float,
        reference_price: float,
        reason: str,
    ) -> None:
        self._logger.warning(
            "risk control rejected order symbol={} side={} amount={} price={} reason={}",
            symbol,
            side.value,
            amount,
            reference_price,
            reason,
        )
        raise RiskControlError(reason)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= _EPS:
        return 0.0
    return max(0.0, numerator / denominator)


def _as_positive_ratio(values: Mapping[str, Any], key: str) -> float:
    raw = values.get(key)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise RiskControlError(f"risk.{key} must be numeric")
    parsed = float(raw)
    if parsed <= 0 or parsed > 1:
        raise RiskControlError(f"risk.{key} must be in (0, 1]")
    return parsed


def _as_non_negative_ratio(values: Mapping[str, Any], key: str) -> float:
    raw = values.get(key)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise RiskControlError(f"risk.{key} must be numeric")
    parsed = float(raw)
    if parsed < 0 or parsed > 1:
        raise RiskControlError(f"risk.{key} must be in [0, 1]")
    return parsed


def _resolve_reference_price(
    *,
    symbol: str,
    entry_price: float,
    current_price: object,
    price_overrides: Mapping[str, float],
) -> float:
    if symbol in price_overrides:
        override = float(price_overrides[symbol])
        if override <= 0:
            raise RiskControlError(f"reference price for {symbol} must be > 0")
        return override

    if isinstance(current_price, (int, float)) and not isinstance(current_price, bool):
        resolved = float(current_price)
        if resolved > 0:
            return resolved

    if entry_price <= 0:
        raise RiskControlError(f"entry price for {symbol} must be > 0")
    return entry_price
