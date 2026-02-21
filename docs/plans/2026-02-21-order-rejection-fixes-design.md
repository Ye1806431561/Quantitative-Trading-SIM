# Order Rejection Fixes Design

## Scope
- Release frozen funds when an order is rejected (PENDING -> REJECTED).
- Remove nested transaction usage inside `update_order_status()`.
- Update documentation to reflect verified test results and correct step wording.

## Behavior
- When `update_order_status(..., REJECTED)` is called for a BUY order, release the unfilled frozen funds using `AccountService.release_funds`.
- Avoid `with tx:` nesting inside a transaction; use `tx.execute(...)` directly.

## Tests
- Add a test ensuring BUY order frozen funds are released on REJECTED.
- Run the full test suite and use actual results in documentation.

## Docs
- Replace any “59 passed” statements with the actual full test results.
- Narrow `findings.md` requirement wording to Step 12.
