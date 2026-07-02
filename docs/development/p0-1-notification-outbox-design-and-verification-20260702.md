# P0-1 Notification Outbox — Design & Verification

**Date:** 2026-07-02  
**Slice:** P0-① first implementation cut after
`p0-1-notification-outbox-taskbook-20260702.md`.

## 1. What Shipped

- Persistent `NotificationOutbox` for the logical event snapshot.
- Persistent `NotificationDelivery` for one recipient/channel delivery row.
- `NotificationService.notify(...)` now enqueues durable rows inside the caller's
  current SQLAlchemy transaction instead of writing a log-only message.
- `NotificationOutboxWorker` drains due delivery rows, claims/reclaims stale rows,
  calls a channel adapter, marks `sent`, schedules retry, or terminally fails.
- `yuantus notification-worker` CLI entrypoint, including `--once`, `--tenant`,
  and `--org` parity with the existing publication workers.
- Default `null` adapter performs no remote I/O and deterministically marks rows
  as sent; SMTP is opt-in via settings and fails closed when host/from config is
  incomplete.

## 2. Reliability Rules

- The in-memory after-commit `EventBus` remains trigger-only. Critical business
  paths call `NotificationService.notify(...)` in their transaction so the
  notification outbox commits atomically with the business state.
- Remote I/O is never done in the caller transaction. The worker is the only
  delivery path.
- Missing recipient email becomes a terminal `recipient_missing` failed delivery,
  not an exception that can roll back the business transaction.
- Idempotency is content-derived for this first cut: same event/payload/recipient
  set reuses the existing logical outbox row; a changed payload is a new logical
  notification.

## 3. Boundaries

Included now:

- explicit `recipients` passed to `NotificationService.notify(...)`;
- email-shaped recipient keys and numeric `RBACUser.id` recipients;
- retry/dead-letter worker state machine;
- tenant baseline + Alembic migration coverage.

Deferred:

- subscription model / role expansion;
- digest/coalescing;
- IM/webhook channels;
- notification center UI;
- distributed worker coordination beyond PostgreSQL `SKIP LOCKED` / SQLite
  fallback parity with the existing publication workers.

## 4. Verification

Local commands run before PR:

```bash
PYTHONPATH=src /Users/chouhua/Downloads/Github/Yuantus/.venv-wp13/bin/python -m pytest -q \
  src/yuantus/meta_engine/tests/test_notification_outbox.py \
  src/yuantus/meta_engine/tests/test_notification_worker_cli.py
```

Expected result: `13 passed`.

The test suite pins:

- `NotificationService.notify(...)` writes one durable outbox + delivery;
- duplicate same event/payload/recipient set does not fan out twice;
- explicit idempotency-key reuse with changed payload is rejected;
- missing email is terminal `recipient_missing`;
- null adapter drains a delivery to `sent`;
- SMTP adapter selection fails closed when host/from are missing;
- retryable failures reschedule then dead-letter at `max_attempts`;
- stale claims are reclaimed and future rows are not claimed.
- `yuantus notification-worker` is registered and dispatches `--once` /
  daemon mode without touching the database in the CLI test.

Additional guards:

- `scripts/generate_tenant_baseline.py` regenerated
  `migrations_tenant/versions/t1_initial_tenant_baseline.py`;
- `.github/workflows/ci.yml` explicitly lists
  `test_notification_outbox.py`;
- `conftest.py` allowlist includes the new DB-backed test file.
