# Order Idempotency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add optional `order_id` to `CreateOrderRequest` and enforce idempotent order creation with strict mismatch rejection.

**Architecture:** Keep schema unchanged and implement idempotency at the service layer. If `order_id` is provided, look up existing order, compare fields, and either return or raise; otherwise create a new order. Guard against insert races by catching uniqueness conflicts and re-checking.

**Tech Stack:** Python 3.10+, SQLite, pytest.

---

### Task 1: Add failing tests for idempotent create

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py`

**Step 1: Write failing tests**

```python

def test_create_order_idempotent_returns_existing(order_service):
    request = CreateOrderRequest(
        order_id="ORD-TEST-IDEMPOTENT",
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    created = order_service.create_order(request)
    repeated = order_service.create_order(request)
    assert repeated.id == created.id
    assert repeated.symbol == created.symbol
    assert repeated.price == created.price


def test_create_order_idempotent_rejects_mismatch(order_service):
    request = CreateOrderRequest(
        order_id="ORD-TEST-MISMATCH",
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order_service.create_order(request)

    mismatch = CreateOrderRequest(
        order_id="ORD-TEST-MISMATCH",
        symbol="ETH/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    with pytest.raises(OrderServiceError, match="order_id already exists"):
        order_service.create_order(mismatch)
```

**Step 2: Run tests to verify failure**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py::test_create_order_idempotent_returns_existing`
Expected: FAIL (CreateOrderRequest has no `order_id` or mismatch is not handled)

---

### Task 2: Implement order_id support and idempotent logic

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/src/core/order_service.py`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py`

**Step 1: Update request model**

```python
@dataclass(frozen=True)
class CreateOrderRequest:
    order_id: str | None
    symbol: str
    type: OrderType
    side: OrderSide
    amount: float
    price: float | None = None
```

**Step 2: Implement idempotent create**

```python
order_id = request.order_id or self._generate_order_id()

with self._db.transaction() as tx:
    existing = tx.execute(
        "SELECT id, symbol, type, side, price, amount, filled, status, created_at, updated_at "
        "FROM orders WHERE id = ?;",
        (order_id,),
    ).fetchone()
    if existing is not None:
        existing_order = Order.validate(dict(existing))
        if not self._matches_request(existing_order, request):
            raise OrderServiceError("order_id already exists with different fields")
        return existing_order

    # ... (freeze funds if BUY, then insert)
```

Add helper:

```python
@staticmethod
def _matches_request(order: Order, request: CreateOrderRequest) -> bool:
    return (
        order.symbol == request.symbol.strip()
        and order.type == request.type
        and order.side == request.side
        and order.amount == request.amount
        and order.price == request.price
    )
```

**Step 3: Handle uniqueness race (optional but safe)**

```python
except sqlite3.IntegrityError:
    existing = tx.execute(...).fetchone()
    if existing is None:
        raise
    existing_order = Order.validate(dict(existing))
    if not self._matches_request(existing_order, request):
        raise OrderServiceError("order_id already exists with different fields")
    return existing_order
```

**Step 4: Run tests to verify pass**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py::test_create_order_idempotent_returns_existing`
Expected: PASS

**Step 5: Run full order service tests**

Run: `PYTHONPATH=. ./.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py`
Expected: PASS

**Step 6: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/src/core/order_service.py /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py
git commit -m "feat: add order_id idempotency for order creation"
```

---

### Task 3: Update memory-bank notes for idempotency semantics

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/progress.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/findings.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/architecture.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/requirements-traceability-checklist.md`

**Step 1: Clarify idempotency requires order_id**
- Replace wording like “创建幂等” with “当调用方提供 `order_id` 时创建幂等”。

**Step 2: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/progress.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/findings.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/architecture.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/requirements-traceability-checklist.md
git commit -m "docs: clarify order_id idempotency requirement"
```
