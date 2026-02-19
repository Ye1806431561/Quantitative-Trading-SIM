"""Pricing service for portfolio valuation and position assessment."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from src.core.account_service import AccountService
from src.core.database import SQLiteDatabase
from src.core.position import Position
from src.data.realtime_payloads import RealtimeMarketSnapshot


class PriceServiceError(RuntimeError):
    """Raised when pricing/valuation cannot be completed safely."""


class PriceSnapshotReader(Protocol):
    """Interface required by PriceService for latest-price reads."""

    def get_latest_price(self, symbol: str) -> RealtimeMarketSnapshot:
        ...


@dataclass(frozen=True)
class PositionAssessment:
    """Valuation result for one position at a specific mark price."""

    symbol: str
    amount: float
    entry_price: float
    mark_price: float
    market_value: float
    unrealized_pnl: float


@dataclass(frozen=True)
class PortfolioValuation:
    """Aggregated valuation output used by live monitoring/CLI."""

    positions: Sequence[PositionAssessment]
    base_cash: float
    positions_value: float
    total_assets: float
    priced_at_ms: int


class PriceService:
    """Use latest market prices to value assets and assess positions."""

    def __init__(
        self,
        database: SQLiteDatabase,
        account_service: AccountService,
        market_reader: PriceSnapshotReader,
        *,
        now_ms_fn: Callable[[], int] | None = None,
    ) -> None:
        self._db = database
        self._account_service = account_service
        self._market_reader = market_reader
        self._now_ms_fn = now_ms_fn or (lambda: int(time.time() * 1000))

    def valuate_portfolio(self) -> PortfolioValuation:
        """Reprice all persisted positions and return portfolio valuation."""
        positions = self._account_service.load_positions()
        assessments: list[PositionAssessment] = []
        price_lookup: dict[str, float] = {}
        fetched_at_ms: list[int] = []

        for position in positions:
            mark_price, fetched_at = self._resolve_mark_price(position)
            market_value = position.amount * mark_price
            unrealized_pnl = (mark_price - position.entry_price) * position.amount

            assessments.append(
                PositionAssessment(
                    symbol=position.symbol,
                    amount=position.amount,
                    entry_price=position.entry_price,
                    mark_price=mark_price,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                )
            )
            price_lookup[position.symbol] = mark_price
            fetched_at_ms.append(fetched_at)

        self._persist_assessments(assessments)

        total_assets = self._account_service.compute_total_assets(price_lookup)
        positions_value = sum(item.market_value for item in assessments)
        base_cash = total_assets - positions_value

        return PortfolioValuation(
            positions=assessments,
            base_cash=base_cash,
            positions_value=positions_value,
            total_assets=total_assets,
            priced_at_ms=max(fetched_at_ms, default=self._now_ms_fn()),
        )

    def _resolve_mark_price(self, position: Position) -> tuple[float, int]:
        try:
            snapshot = self._market_reader.get_latest_price(position.symbol)
        except Exception as exc:  # pragma: no cover - covered through calling behavior
            raise PriceServiceError(
                f"failed to fetch latest price for {position.symbol}: {exc}"
            ) from exc

        mark_price = self._extract_last_price(snapshot.data)
        if mark_price is None:
            if position.current_price is None:
                raise PriceServiceError(f"missing mark price for symbol {position.symbol}")
            mark_price = float(position.current_price)

        if mark_price <= 0:
            raise PriceServiceError(f"mark price must be > 0 for symbol {position.symbol}")

        return mark_price, int(snapshot.fetched_at_ms)

    @staticmethod
    def _extract_last_price(data: Mapping[str, Any]) -> float | None:
        raw_price = data.get("last_price")
        if raw_price is None:
            return None
        if not isinstance(raw_price, (int, float)) or isinstance(raw_price, bool):
            raise PriceServiceError("snapshot.data.last_price must be numeric")
        return float(raw_price)

    def _persist_assessments(self, assessments: Sequence[PositionAssessment]) -> None:
        if not assessments:
            return
        with self._db.transaction() as tx:
            for item in assessments:
                tx.execute(
                    """
                    UPDATE positions
                    SET current_price = ?, unrealized_pnl = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE symbol = ?;
                    """,
                    (item.mark_price, item.unrealized_pnl, item.symbol),
                )
