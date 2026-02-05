#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


def main() -> int:
    file_id = (os.environ.get("FILE_ID") or "").strip()
    if not file_id:
        print("Missing FILE_ID", file=sys.stderr)
        return 2

    tenant = (os.environ.get("TENANT") or os.environ.get("YUANTUS_TENANT_ID") or "").strip()
    org = (os.environ.get("ORG") or os.environ.get("YUANTUS_ORG_ID") or "").strip()

    if tenant:
        tenant_id_var.set(tenant)
    if org:
        org_id_var.set(org)

    import_all_models()

    with get_db_session() as session:
        result = cad_preview({"file_id": file_id}, session)

    print(json.dumps(result))
    if not result.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parents[1]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    from yuantus.context import org_id_var, tenant_id_var
    from yuantus.database import get_db_session
    from yuantus.meta_engine.bootstrap import import_all_models
    from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_preview

    raise SystemExit(main())
