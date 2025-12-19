from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Optional

import typer
import uvicorn

from yuantus import __version__
from yuantus.config import get_settings
from yuantus.context import org_id_var, tenant_id_var

app = typer.Typer(add_completion=False, help="YuantusPLM CLI")


@app.callback()
def _root() -> None:
    invoked_as = Path(sys.argv[0]).name
    if invoked_as == "plm":
        typer.echo("Deprecated: use `yuantus` instead of `plm`.", err=True)


@app.command()
def start(
    host: Optional[str] = typer.Option(None, help="Bind host"),
    port: Optional[int] = typer.Option(None, help="Bind port"),
    reload: bool = typer.Option(False, help="Auto-reload on changes (dev)"),
) -> None:
    settings = get_settings()
    uvicorn.run(
        "yuantus.api.app:app",
        host=host or settings.HOST,
        port=port or settings.PORT,
        reload=reload,
    )


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command()
def worker(
    worker_id: Optional[str] = typer.Option(None, help="Worker id"),
    poll_interval: int = typer.Option(5, help="Poll interval seconds"),
    once: bool = typer.Option(False, help="Process one job then exit"),
    tenant: Optional[str] = typer.Option(
        None, "--tenant", help="Tenant id (for db-per-tenant/org)"
    ),
    org: Optional[str] = typer.Option(
        None, "--org", help="Org id (for db-per-tenant-org)"
    ),
) -> None:
    """
    Run a background job worker.

    This is a dev-friendly worker that polls the database for pending jobs.
    """
    if tenant is not None:
        tenant_id_var.set(tenant)
    if org is not None:
        org_id_var.set(org)

    from yuantus.meta_engine.services.job_worker import JobWorker
    from yuantus.meta_engine.tasks.cad_conversion_tasks import perform_cad_conversion
    from yuantus.meta_engine.tasks.cad_pipeline_tasks import (
        cad_dedup_vision,
        cad_geometry,
        cad_ml_vision,
        cad_preview,
    )

    w = JobWorker(worker_id or "worker-1", poll_interval=poll_interval)
    w.register_handler("cad_conversion", perform_cad_conversion)
    w.register_handler("cad_preview", cad_preview)
    w.register_handler("cad_geometry", cad_geometry)
    w.register_handler("cad_dedup_vision", cad_dedup_vision)
    w.register_handler("cad_ml_vision", cad_ml_vision)

    if once:
        processed = w.run_once()
        if processed:
            typer.echo("Processed one job.")
        else:
            typer.echo("No pending jobs.")
        return

    w.start()
    typer.echo(f"Worker '{w.worker_id}' started. Press Ctrl+C to stop.", err=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()
        typer.echo(f"Worker '{w.worker_id}' stopped.", err=True)


@app.command("seed-identity")
def seed_identity(
    tenant: str = typer.Option("tenant-1", help="Tenant id"),
    org: str = typer.Option("org-1", help="Org id"),
    username: str = typer.Option("admin", help="Username"),
    password: str = typer.Option("admin", help="Password (dev only)"),
    email: str = typer.Option("admin@example.com", help="Email"),
    user_id: int = typer.Option(1, help="Identity user id (int)"),
    roles: str = typer.Option("admin", help="Comma-separated role names"),
    superuser: bool = typer.Option(True, help="Grant superuser"),
) -> None:
    """
    Seed identity DB for development: tenant/org/user/membership.
    """
    from yuantus.security.auth.database import get_identity_db_session, init_identity_db
    from yuantus.security.auth.models import AuthUser
    from yuantus.security.auth.service import AuthService

    init_identity_db(create_tables=True)
    role_list = [r.strip() for r in (roles or "").split(",") if r.strip()]

    with get_identity_db_session() as session:
        svc = AuthService(session)
        svc.ensure_tenant(tenant, name=tenant)
        svc.ensure_org(tenant, org, name=org)

        existing = (
            session.query(AuthUser)
            .filter(AuthUser.tenant_id == tenant, AuthUser.username == username)
            .first()
        )
        if not existing:
            user = svc.create_user(
                tenant_id=tenant,
                username=username,
                password=password,
                email=email,
                is_superuser=superuser,
                user_id=user_id,
            )
        else:
            existing.is_active = True
            existing.is_superuser = bool(superuser)
            svc.set_password(tenant_id=tenant, username=username, password=password)
            user = existing

        svc.add_membership(
            tenant_id=tenant, org_id=org, user_id=user.id, roles=role_list
        )

    typer.echo(f"Seeded identity: tenant={tenant}, org={org}, user={username} ({user_id})")


@app.command("seed-meta")
def seed_meta(
    tenant: Optional[str] = typer.Option(
        None, "--tenant", help="Tenant id (used when TENANCY_MODE=db-per-tenant)"
    ),
    org: Optional[str] = typer.Option(
        None, "--org", help="Org id (used when TENANCY_MODE=db-per-tenant-org)"
    )
) -> None:
    """
    Seed minimal Meta Engine schema (ItemType/Property) for local development.
    """
    from yuantus.config import get_settings
    from yuantus.database import (
        SessionLocal as GlobalSessionLocal,
        engine as GlobalEngine,
        get_engine_for_scope,
        get_engine_for_tenant,
        get_sessionmaker_for_scope,
        get_sessionmaker_for_tenant,
        init_db,
    )
    from yuantus.meta_engine.bootstrap import import_all_models
    from yuantus.meta_engine.models.meta_schema import ItemType, Property
    from yuantus.meta_engine.permission.models import Access, Permission
    from yuantus.models.base import Base
    from yuantus.security.rbac.models import RBACRole, RBACUser

    settings = get_settings()
    if settings.TENANCY_MODE == "db-per-tenant-org":
        engine = get_engine_for_scope(tenant, org)
        SessionLocal = get_sessionmaker_for_scope(tenant, org)
    elif settings.TENANCY_MODE == "db-per-tenant":
        engine = get_engine_for_tenant(tenant)
        SessionLocal = get_sessionmaker_for_tenant(tenant)
    else:
        engine = GlobalEngine
        SessionLocal = GlobalSessionLocal

    import_all_models()
    init_db(create_tables=True, bind_engine=engine)

    session = SessionLocal()
    try:
        # Dev identity baseline (needed by VersionHistory FK constraints)
        admin_user = session.get(RBACUser, 1)
        if not admin_user:
            admin_user = RBACUser(
                id=1,
                user_id=1,
                username="admin",
                email="admin@example.com",
                is_active=True,
                is_superuser=True,
            )
            session.add(admin_user)

        admin_role = session.query(RBACRole).filter_by(name="admin").first()
        if not admin_role:
            admin_role = RBACRole(
                name="admin",
                display_name="Admin",
                description="Built-in admin role (dev)",
                is_system=True,
                is_active=True,
                priority=1000,
            )
            session.add(admin_role)
            session.flush()

        if admin_role not in (admin_user.roles or []):
            admin_user.roles.append(admin_role)

        default_perm = session.get(Permission, "Default")
        if not default_perm:
            default_perm = Permission(id="Default", name="Default (dev)")
            session.add(default_perm)
            session.add(
                Access(
                    id="Default:world",
                    permission=default_perm,
                    identity_id="world",
                    can_create=True,
                    can_get=True,
                    can_update=True,
                    can_delete=True,
                    can_discover=True,
                )
            )

        part = session.get(ItemType, "Part")
        if not part:
            part = ItemType(id="Part", label="Part", is_versionable=True)
            session.add(part)
        if not part.permission_id:
            part.permission_id = default_perm.id

        props = [
            Property(
                name="item_number",
                label="Part Number",
                is_required=True,
                length=32,
                data_type="string",
            ),
            Property(name="name", label="Name", length=128, data_type="string"),
            Property(
                name="description",
                label="Description",
                length=256,
                data_type="string",
            ),
            Property(name="state", label="State", default_value="New", data_type="string"),
            Property(name="cost", label="Cost", data_type="float"),
            Property(name="weight", label="Weight", data_type="float"),
        ]
        existing_prop_names = {p.name for p in (part.properties or [])}
        for prop in props:
            if prop.name in existing_prop_names:
                continue
            prop.item_type = part
            session.add(prop)

        part_bom = session.get(ItemType, "Part BOM")
        if not part_bom:
            part_bom = ItemType(id="Part BOM", label="Part BOM", is_relationship=True)
            part_bom.source_item_type_id = "Part"
            part_bom.related_item_type_id = "Part"
            session.add(part_bom)
        if not part_bom.permission_id:
            part_bom.permission_id = default_perm.id

        if not any(p.name == "quantity" for p in (part_bom.properties or [])):
            session.add(
                Property(
                    item_type=part_bom,
                    name="quantity",
                    label="Quantity",
                    data_type="float",
                    default_value="1.0",
                )
            )

        session.commit()
        typer.echo("Seeded meta schema: Part, Part BOM")
    finally:
        session.close()


@app.command("db")
def db_command(
    action: str = typer.Argument(
        ..., help="upgrade|downgrade|revision|current|history"
    ),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Migration message (for revision)"
    ),
    autogenerate: bool = typer.Option(
        True, "--autogenerate/--no-autogenerate", help="Autogenerate migration"
    ),
    revision: Optional[str] = typer.Option(
        None, "--revision", "-r", help="Target revision (for upgrade/downgrade)"
    ),
) -> None:
    """
    Database migrations via Alembic.

    Actions:
      upgrade   - Apply migrations (default: head)
      downgrade - Revert migrations
      revision  - Create new migration
      current   - Show current revision
      history   - Show migration history
    """
    import os
    import subprocess
    import sys

    # Find alembic.ini
    alembic_ini = os.path.join(os.getcwd(), "alembic.ini")
    if not os.path.exists(alembic_ini):
        # Try package directory
        pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini = os.path.join(pkg_dir, "alembic.ini")
        if not os.path.exists(alembic_ini):
            typer.echo("Error: alembic.ini not found", err=True)
            raise typer.Exit(1)

    # Build alembic command
    cmd = [sys.executable, "-m", "alembic", "-c", alembic_ini]

    if action == "upgrade":
        target = revision or "head"
        cmd.extend(["upgrade", target])
    elif action == "downgrade":
        target = revision or "-1"
        cmd.extend(["downgrade", target])
    elif action == "revision":
        cmd.append("revision")
        if autogenerate:
            cmd.append("--autogenerate")
        if message:
            cmd.extend(["-m", message])
        else:
            typer.echo("Warning: No message provided, using default", err=True)
            cmd.extend(["-m", "auto migration"])
    elif action == "current":
        cmd.append("current")
    elif action == "history":
        cmd.append("history")
    else:
        typer.echo(f"Unknown action: {action}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Running: {' '.join(cmd)}", err=True)
    result = subprocess.run(cmd, cwd=os.getcwd())
    raise typer.Exit(result.returncode)


@app.command("init-storage")
def init_storage(
    bucket: Optional[str] = typer.Option(None, help="Bucket name (default: from settings)"),
) -> None:
    """
    Initialize S3/MinIO storage bucket.

    Creates the bucket if it doesn't exist.
    Only needed for STORAGE_TYPE=s3.
    """
    from yuantus.config import get_settings

    settings = get_settings()
    if settings.STORAGE_TYPE != "s3":
        typer.echo(f"Storage type is '{settings.STORAGE_TYPE}', not 's3'. Nothing to initialize.")
        return

    bucket_name = bucket or settings.S3_BUCKET_NAME

    try:
        import boto3
        from botocore.exceptions import ClientError

        s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION_NAME,
        )

        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            typer.echo(f"Bucket '{bucket_name}' already exists.")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket"):
                # Create bucket
                try:
                    if settings.S3_REGION_NAME == "us-east-1":
                        s3_client.create_bucket(Bucket=bucket_name)
                    else:
                        s3_client.create_bucket(
                            Bucket=bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": settings.S3_REGION_NAME
                            },
                        )
                    typer.echo(f"Created bucket '{bucket_name}'.")
                except ClientError as create_error:
                    typer.echo(f"Error creating bucket: {create_error}", err=True)
                    raise typer.Exit(1)
            else:
                typer.echo(f"Error checking bucket: {e}", err=True)
                raise typer.Exit(1)

    except ImportError:
        typer.echo("Error: boto3 not installed. Run: pip install boto3", err=True)
        raise typer.Exit(1)


def main() -> None:
    app()
