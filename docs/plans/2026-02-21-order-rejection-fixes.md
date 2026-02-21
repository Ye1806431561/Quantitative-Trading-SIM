# Order Rejection Fixes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Release frozen funds on order rejection, remove nested transactions, and sync documentation with verified test results.

**Architecture:** Keep schema unchanged. Add rejection handling in `OrderService.update_order_status()`, remove nested `with tx:` usage, and cover with a focused test. Run the full test suite and update memory-bank documents with the actual results.

**Tech Stack:** Python 3.10+, SQLite, pytest.

---

### Task 1: Add failing test for REJECTED fund release

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py`

**Step 1: Write failing test**

```python

def test_update_order_status_rejected_releases_frozen_funds(order_service, account_service):
    request = CreateOrderRequest(
        symbol="BTC/USDT",
        type=OrderType.LIMIT,
        side=OrderSide.BUY,
        amount=0.5,
        price=50000.0,
    )
    order = order_service.create_order(request)

    account_before = account_service.get_account("USDT")
    assert account_before.frozen == 25000.0

    rejected = order_service.update_order_status(order.id, OrderStatus.REJECTED)
    assert rejected.status == OrderStatus.REJECTED

    account_after = account_service.get_account("USDT")
    assert account_after.frozen == 0.0
    assert account_after.available == 100000.0
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py::test_update_order_status_rejected_releases_frozen_funds`
Expected: FAIL (frozen funds not released)

---

### Task 2: Implement REJECTED release + remove nested transaction

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/src/core/order_service.py`

**Step 1: Remove nested `with tx:` block**

Replace:
```python
with tx:
    tx.execute(...)
```
with direct `tx.execute(...)`.

**Step 2: Release frozen funds for REJECTED**

Add in `update_order_status()` before status update:
```python
if new_status == OrderStatus.REJECTED and order.side == OrderSide.BUY:
    unfilled_amount = order.amount - new_filled
    if unfilled_amount > 0:
        if order.price is None:
            raise OrderServiceError("cannot release funds: order price is None")
        frozen_funds = unfilled_amount * order.price
        base_currency = self._extract_quote_currency(order.symbol)
        self._account_service.release_funds(base_currency, frozen_funds)
```

**Step 3: Run test to verify pass**

Run: `PYTHONPATH=. /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py::test_update_order_status_rejected_releases_frozen_funds`
Expected: PASS

**Step 4: Run full order service tests**

Run: `PYTHONPATH=. /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py`
Expected: PASS

**Step 5: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/src/core/order_service.py /Users/pingu/Documents/Quantitative-Trading-SIM/tests/test_order_service.py
git commit -m "fix: release frozen funds on rejected orders"
```

---

### Task 3: Run full test suite and update memory-bank docs

**Files:**
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/progress.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/findings.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/architecture.md`
- Modify: `/Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/requirements-traceability-checklist.md`

**Step 1: Run full test suite**

Run: `PYTHONPATH=. /Users/pingu/Documents/Quantitative-Trading-SIM/.venv/bin/pytest -q`
Expected: PASS (capture actual counts)

**Step 2: Update documentation**
- Replace “全量测试 59 passed/通过” with the actual test results from Step 1.
- Fix `findings.md` wording: change “执行 implementation-plan 第 1-12 步” to “执行 implementation-plan 第 12 步”。

**Step 3: Commit**

```bash
git add /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/progress.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/findings.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/architecture.md /Users/pingu/Documents/Quantitative-Trading-SIM/memory-bank/requirements-traceability-checklist.md
git commit -m "docs: sync test results and step 12 scope"
```
