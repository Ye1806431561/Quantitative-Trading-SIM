"""Order state machine definition and transition helpers (Phase 2 Step 23)."""

from __future__ import annotations

from src.core.enums import OrderStatus

# "new" in the implementation plan maps to persisted status "pending".
ORDER_NEW_STATUS = OrderStatus.PENDING

VALID_ORDER_STATUS_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {
        OrderStatus.OPEN,
        OrderStatus.REJECTED,
        OrderStatus.CANCELED,
    },
    OrderStatus.OPEN: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
    },
    OrderStatus.PARTIALLY_FILLED: {
        OrderStatus.PARTIALLY_FILLED,
        OrderStatus.FILLED,
        OrderStatus.CANCELED,
    },
    OrderStatus.FILLED: set(),
    OrderStatus.CANCELED: set(),
    OrderStatus.REJECTED: set(),
}


def can_transition(current: OrderStatus, target: OrderStatus) -> bool:
    """Return True when `current -> target` is a legal state transition."""
    return target in VALID_ORDER_STATUS_TRANSITIONS.get(current, set())


def get_valid_next_statuses(current: OrderStatus) -> set[OrderStatus]:
    """Return legal next statuses for an order state."""
    return set(VALID_ORDER_STATUS_TRANSITIONS.get(current, set()))
