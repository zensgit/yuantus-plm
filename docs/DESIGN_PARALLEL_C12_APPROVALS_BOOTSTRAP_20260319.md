# C12 – Generic Approvals Bootstrap

## Objective

Provide a reusable, entity-agnostic approval workflow that any domain
(ECO, purchase order, quality deviation, maintenance work-order, etc.)
can bind to via `entity_type` + `entity_id`.

## Domain Model

### Enums

| Enum | Values |
|------|--------|
| `ApprovalState` | draft, pending, approved, rejected, cancelled |
| `ApprovalPriority` | low, normal, high, urgent |

### Tables

| Table | Key Columns |
|-------|-------------|
| `meta_approval_categories` | id, name, parent_id, description, created_at |
| `meta_approval_requests` | id, title, category_id, entity_type, entity_id, state, priority, description, rejection_reason, requested_by_id, assigned_to_id, decided_by_id, timestamps, properties (JSONB) |

### State Machine

```
draft ──► pending ──► approved   (terminal)
  │          │
  │          └──► rejected ──► pending  (resubmission)
  │          │
  │          └──► cancelled  (terminal)
  └──────────────► cancelled  (terminal)
```

## Service Layer – `ApprovalService`

| Method | Description |
|--------|-------------|
| `create_category` | Create taxonomy node with optional parent |
| `list_categories` | List all categories ordered by name |
| `create_request` | Create new request in draft state; validates priority |
| `get_request` | Fetch single request by id |
| `list_requests` | Filtered list (state, category, entity_type, entity_id, priority, assigned_to) |
| `transition_request` | State machine transition with timestamp/decided_by bookkeeping |
| `get_summary` | Aggregate counts by state and priority with optional filters |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/approvals/categories` | Create category |
| GET  | `/approvals/categories` | List categories |
| POST | `/approvals/requests` | Create request |
| GET  | `/approvals/requests` | List requests (6 query filters) |
| GET  | `/approvals/requests/{request_id}` | Get single request |
| POST | `/approvals/requests/{request_id}/transition` | State transition |
| GET  | `/approvals/summary` | Aggregate summary |

## Dependencies

- SQLAlchemy ORM (Base from `yuantus.models.base`)
- FastAPI router with `get_db` and `get_current_user_id_optional`
- PostgreSQL JSONB for extensible properties column

## Files

| Path | Purpose |
|------|---------|
| `src/yuantus/meta_engine/approvals/__init__.py` | Package marker |
| `src/yuantus/meta_engine/approvals/models.py` | Domain models + enums |
| `src/yuantus/meta_engine/approvals/service.py` | Business logic |
| `src/yuantus/meta_engine/web/approvals_router.py` | API endpoints |
| `src/yuantus/meta_engine/tests/test_approvals_service.py` | Service tests |
| `src/yuantus/meta_engine/tests/test_approvals_router.py` | Router tests |
