#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx


TARGET_KEYS = [
    "part_number",
    "part_name",
    "material",
    "weight",
    "revision",
    "drawing_no",
    "author",
    "created_at",
]

CAD_EXTENSIONS = {
    "step",
    "stp",
    "iges",
    "igs",
    "sldprt",
    "sldasm",
    "ipt",
    "iam",
    "prt",
    "asm",
    "catpart",
    "catproduct",
    "par",
    "psm",
    "3dm",
    "dwg",
    "dxf",
    "stl",
    "obj",
    "gltf",
    "glb",
    "jt",
    "x_t",
    "x_b",
}


def _resolve_extension_for_file(path: Path) -> str:
    name = path.name.lower()
    match = re.search(r"\.(?P<ext>prt|asm)\.\d+$", name)
    if match:
        return match.group("ext")
    return path.suffix.lower().lstrip(".")


def _is_nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _normalize_upload_name(path: Path) -> str:
    name = path.name
    match = re.match(r"^(?P<stem>.+)\.(?P<ext>prt|asm)\.(?P<rev>\d+)$", name, re.I)
    if match:
        return f"{match.group('stem')}.{match.group('ext')}"
    return name


def _is_candidate_file(path: Path, extensions: Tuple[str, ...]) -> bool:
    name = path.name.lower()
    if re.search(r"\.(prt|asm)\.\d+$", name):
        ext = _resolve_extension_for_file(path)
        return not extensions or ext in extensions
    ext = _resolve_extension_for_file(path)
    if extensions:
        return ext in extensions
    return ext in CAD_EXTENSIONS


def _seed_identity_meta(
    cli: str,
    tenant: str,
    org: str,
    env: Dict[str, str],
) -> None:
    if not cli or not Path(cli).exists():
        return
    cmd = [cli, "seed-identity", "--tenant", tenant, "--org", org, "--username", "admin", "--password", "admin", "--user-id", "1", "--roles", "admin", "--superuser"]
    subprocess.run(cmd, check=True, env=env)
    cmd = [cli, "seed-meta", "--tenant", tenant, "--org", org]
    subprocess.run(cmd, check=True, env=env)


def _run_direct_extract(tenant: str, org: str, file_id: str) -> Dict[str, Any]:
    from yuantus.context import org_id_var, tenant_id_var
    from yuantus.database import get_db_session
    from yuantus.meta_engine.bootstrap import import_all_models
    from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

    tenant_id_var.set(tenant)
    org_id_var.set(org)
    import_all_models()

    with get_db_session() as session:
        return cad_extract({"file_id": file_id}, session)


def _auth_token(client: httpx.Client, base_url: str, tenant: str, org: str) -> str:
    resp = client.post(
        f"{base_url}/api/v1/auth/login",
        json={"tenant_id": tenant, "username": "admin", "password": "admin", "org_id": org},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token") or ""
    if not token:
        raise RuntimeError("Missing access_token from login response")
    return token


def _collect_files(target_dir: Path, extensions: Tuple[str, ...]) -> List[Path]:
    files: List[Path] = []
    for entry in sorted(target_dir.iterdir()):
        if entry.is_file() and not entry.name.startswith("."):
            if _is_candidate_file(entry, extensions):
                files.append(entry)
    return files


def _write_report(
    output_path: Path,
    *,
    report_title: str,
    base_url: str,
    extractor_url: str,
    tenant: str,
    org: str,
    cad_format: str,
    cad_connector_id: str,
    target_dir: Path,
    extensions: Tuple[str, ...],
    results: List[Dict[str, Any]],
) -> None:
    total = len(results)
    key_counts = {key: 0 for key in TARGET_KEYS}
    key_presence: Dict[str, int] = {}

    for result in results:
        attrs = result.get("attributes", {})
        for key in TARGET_KEYS:
            if _is_nonempty(attrs.get(key)):
                key_counts[key] += 1
        for key, value in (attrs or {}).items():
            if _is_nonempty(value):
                key_presence[key] = key_presence.get(key, 0) + 1

    lines: List[str] = []
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines.append(f"# {report_title} ({target_dir.name})")
    lines.append("")
    lines.append("## Run Info")
    lines.append(f"- Time: `{timestamp}`")
    lines.append(f"- Base URL: `{base_url}`")
    lines.append(f"- Extractor: `{extractor_url}`")
    lines.append(f"- Tenant/Org: `{tenant}` / `{org}`")
    lines.append(f"- CAD Format Override: `{cad_format}`")
    if cad_connector_id:
        lines.append(f"- CAD Connector Override: `{cad_connector_id}`")
    lines.append(f"- Directory: `{target_dir}`")
    if extensions:
        lines.append(f"- Extensions: `{', '.join(extensions)}`")
    lines.append(f"- Files: `{total}`")
    lines.append("")

    lines.append("## Target Field Coverage")
    lines.append("")
    lines.append("| Field | Present | Coverage |")
    lines.append("| --- | --- | --- |")
    for key in TARGET_KEYS:
        count = key_counts[key]
        percent = f"{(count / total * 100):.1f}%" if total else "0.0%"
        lines.append(f"| `{key}` | {count}/{total} | {percent} |")
    lines.append("")

    lines.append("## Extracted Key Distribution (Non-empty)")
    lines.append("")
    lines.append("| Key | Files |")
    lines.append("| --- | --- |")
    for key, count in sorted(key_presence.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{key}` | {count} |")
    lines.append("")

    lines.append("## Per-file Summary")
    lines.append("")
    lines.append("| File | Upload Name | File ID | CAD Format | Connector | Keys |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for result in results:
        file_name = result.get("file_name", "")
        upload_name = result.get("upload_name", "")
        file_id = result.get("file_id", "")
        cad_format = result.get("cad_format", "")
        connector_id = result.get("cad_connector_id", "")
        attrs = result.get("attributes", {})
        keys = ", ".join(sorted([key for key, value in attrs.items() if _is_nonempty(value)]))
        lines.append(
            f"| `{file_name}` | `{upload_name}` | `{file_id}` | `{cad_format}` | "
            f"`{connector_id}` | {keys} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _prepare_upload_file(path: Path, *, force_unique: bool) -> Tuple[Path, Optional[Path]]:
    if not force_unique:
        return path, None
    suffix = path.suffix
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp.close()
    shutil.copyfile(path, temp.name)
    with open(temp.name, "ab") as fh:
        fh.write(b"\nYUANTUS_FORCE_UNIQUE\n")
    return Path(temp.name), Path(temp.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CAD extractor coverage stats.")
    parser.add_argument("--base-url", default="http://127.0.0.1:7910")
    parser.add_argument("--tenant", default="tenant-1")
    parser.add_argument("--org", default="org-1")
    parser.add_argument("--cad-format", default="CREO")
    parser.add_argument("--cad-connector-id", default="")
    parser.add_argument("--dir", required=True)
    parser.add_argument("--output", default="docs/CAD_EXTRACTOR_COVERAGE_JCB1.md")
    parser.add_argument(
        "--report-title",
        default="CAD Extractor Coverage Report",
        help="Markdown title for the report",
    )
    parser.add_argument("--max-files", type=int, default=0)
    parser.add_argument("--force-unique", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--db-path", default="")
    parser.add_argument("--storage-path", default="")
    parser.add_argument(
        "--extensions",
        default="",
        help="Comma-separated extensions filter (e.g. catpart,stp,igs)",
    )
    args = parser.parse_args()

    target_dir = Path(args.dir).expanduser()
    if not target_dir.exists() or not target_dir.is_dir():
        raise SystemExit(f"Directory not found: {target_dir}")

    cli = os.environ.get("CLI", ".venv/bin/yuantus")
    env = os.environ.copy()

    extractor_url = env.get("YUANTUS_CAD_EXTRACTOR_BASE_URL") or env.get("CAD_EXTRACTOR_BASE_URL") or ""
    if not args.offline:
        _seed_identity_meta(cli, args.tenant, args.org, env)
        if not extractor_url:
            raise SystemExit("Missing YUANTUS_CAD_EXTRACTOR_BASE_URL/CAD_EXTRACTOR_BASE_URL")
    else:
        extractor_url = extractor_url or "offline"

    raw_exts = [item.strip().lower().lstrip(".") for item in args.extensions.split(",")]
    extensions = tuple([item for item in raw_exts if item])

    files = _collect_files(target_dir, extensions)
    if args.max_files > 0:
        files = files[: args.max_files]

    results: List[Dict[str, Any]] = []
    if args.offline:
        from yuantus.config import get_settings
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from yuantus.models import user as _user  # noqa: F401
        from yuantus.models.base import Base
        from yuantus.meta_engine.bootstrap import import_all_models
        from yuantus.meta_engine.models.file import FileContainer
        from yuantus.meta_engine.services.file_service import FileService
        from yuantus.meta_engine.tasks.cad_pipeline_tasks import cad_extract

        db_path = args.db_path or tempfile.NamedTemporaryFile(delete=False, suffix=".db").name
        storage_path = args.storage_path or tempfile.mkdtemp(prefix="yuantus_cad_coverage_")
        os.environ["YUANTUS_DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["YUANTUS_SCHEMA_MODE"] = "create_all"
        os.environ["YUANTUS_TENANCY_MODE"] = "single"
        os.environ["YUANTUS_STORAGE_TYPE"] = "local"
        os.environ["YUANTUS_LOCAL_STORAGE_PATH"] = storage_path
        os.environ["YUANTUS_CAD_EXTRACTOR_BASE_URL"] = ""
        get_settings.cache_clear()

        import_all_models()
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        SessionLocal = sessionmaker(bind=engine)
        file_service = FileService()

        with SessionLocal() as session:
            for path in files:
                upload_name = _normalize_upload_name(path)
                upload_path, cleanup_path = _prepare_upload_file(
                    path, force_unique=args.force_unique
                )
                try:
                    content = upload_path.read_bytes()
                finally:
                    if cleanup_path and cleanup_path.exists():
                        cleanup_path.unlink()
                checksum = hashlib.sha256(content).hexdigest()
                file_id = str(uuid.uuid4())
                ext = _resolve_extension_for_file(path)
                storage_key = f"2d/{file_id[:2]}/{file_id}.{ext or 'dwg'}"
                file_service.upload_file(io.BytesIO(content), storage_key)

                file_container = FileContainer(
                    id=file_id,
                    filename=upload_name,
                    file_type=ext or "dwg",
                    mime_type="application/acad",
                    file_size=len(content),
                    checksum=checksum,
                    system_path=storage_key,
                    document_type="2d",
                    is_native_cad=True,
                    cad_format=args.cad_format,
                    cad_connector_id=args.cad_connector_id or None,
                )
                session.add(file_container)
                session.commit()

                extract_result = cad_extract({"file_id": file_id}, session)
                attrs = extract_result.get("extracted_attributes") or {}

                results.append(
                    {
                        "file_name": path.name,
                        "upload_name": upload_name,
                        "file_id": file_id,
                        "cad_format": args.cad_format,
                        "cad_connector_id": args.cad_connector_id,
                        "attributes": attrs,
                    }
                )
    else:
        with httpx.Client() as client:
            token = _auth_token(client, args.base_url, args.tenant, args.org)
            headers = {
                "Authorization": f"Bearer {token}",
                "x-tenant-id": args.tenant,
                "x-org-id": args.org,
            }

            for path in files:
                upload_name = _normalize_upload_name(path)
                data = {
                    "create_extract_job": "false",
                    "create_preview_job": "false",
                    "create_geometry_job": "false",
                    "create_dedup_job": "false",
                    "create_ml_job": "false",
                }
                if args.cad_format:
                    data["cad_format"] = args.cad_format
                if args.cad_connector_id:
                    data["cad_connector_id"] = args.cad_connector_id
                upload_path, cleanup_path = _prepare_upload_file(
                    path, force_unique=args.force_unique
                )
                try:
                    with upload_path.open("rb") as fh:
                        files_payload = {"file": (upload_name, fh)}
                        resp = client.post(
                            f"{args.base_url}/api/v1/cad/import",
                            headers=headers,
                            data=data,
                            files=files_payload,
                            timeout=120,
                        )
                finally:
                    if cleanup_path and cleanup_path.exists():
                        cleanup_path.unlink()
                resp.raise_for_status()
                payload = resp.json()
                file_id = payload.get("file_id") or ""
                if not file_id:
                    raise RuntimeError(f"Missing file_id for {path.name}")

                extract_result = _run_direct_extract(args.tenant, args.org, file_id)
                attrs = extract_result.get("extracted_attributes") or {}

                results.append(
                    {
                        "file_name": path.name,
                        "upload_name": upload_name,
                        "file_id": file_id,
                        "cad_format": payload.get("cad_format") or args.cad_format,
                        "cad_connector_id": payload.get("cad_connector_id") or args.cad_connector_id,
                        "attributes": attrs,
                    }
                )

    _write_report(
        Path(args.output),
        report_title=args.report_title,
        base_url=args.base_url,
        extractor_url=extractor_url,
        tenant=args.tenant,
        org=args.org,
        cad_format=args.cad_format,
        cad_connector_id=args.cad_connector_id,
        target_dir=target_dir,
        extensions=extensions,
        results=results,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
