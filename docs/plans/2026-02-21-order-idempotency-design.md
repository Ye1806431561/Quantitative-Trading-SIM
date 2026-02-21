# Order Idempotency Design

## Scope
- Add optional `order_id` to `CreateOrderRequest`.
- Enforce idempotent create when `order_id` is provided.
- Reject mismatched fields for existing `order_id`.

## Behavior
- If `order_id` is provided and order exists:
  - Fields match → return existing order, no additional fund freeze.
  - Fields differ → raise `OrderServiceError`.
- If `order_id` is provided and order does not exist → create order normally.
- If `order_id` is not provided → current behavior (generate id).

## Data Model
- No schema changes.
- Idempotency is application-layer only.

## Tests
- Add tests for idempotent create (match vs mismatch).
