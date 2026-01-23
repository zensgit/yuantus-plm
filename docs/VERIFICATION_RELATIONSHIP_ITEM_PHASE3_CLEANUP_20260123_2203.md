# Relationship -> Item Phase 3 Cleanup Verification (2026-01-23 22:03 +0800)

## 环境

- 模式：`db-per-tenant-org`
- 目标租户/组织：`tenant-1/org-1`

## 验证命令

```bash
YUANTUS_TENANCY_MODE=db-per-tenant-org \
YUANTUS_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus \
YUANTUS_DATABASE_URL_TEMPLATE=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_mt_pg__{tenant_id}__{org_id} \
YUANTUS_IDENTITY_DATABASE_URL=postgresql+psycopg://yuantus:yuantus@localhost:55432/yuantus_identity_mt_pg \
  .venv/bin/python - <<'PY'
import uuid
from yuantus.context import tenant_id_var, org_id_var
from yuantus.database import get_sessionmaker_for_scope
from yuantus.meta_engine.relationship.models import Relationship

tenant_id_var.set("tenant-1")
org_id_var.set("org-1")

session = get_sessionmaker_for_scope("tenant-1", "org-1")()

rel = Relationship(
    id=str(uuid.uuid4()),
    relationship_type_id="Part BOM",
    source_id="dummy-source",
    related_id="dummy-related",
)

try:
    session.add(rel)
    session.commit()
    print("UNEXPECTED: write succeeded")
except Exception as exc:
    session.rollback()
    print("BLOCKED:", type(exc).__name__, str(exc))
finally:
    session.close()
PY
```

## 结果摘要

- 写入被阻断，抛出 `RuntimeError`。
- 兼容层写入无法开启。

## 日志

- `docs/RELATIONSHIP_ITEM_PHASE3_CLEANUP_20260123_220359.log`
