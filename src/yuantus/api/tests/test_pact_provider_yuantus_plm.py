from __future__ import annotations

import contextlib
import os
import shutil
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Optional

import pytest
import requests
import uvicorn
from sqlalchemy.orm import sessionmaker

PACT_DOCS_URL = "https://docs.pact.io/implementation_guides/python/docs/provider"
REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PACT_DIR = REPO_ROOT / "contracts" / "pacts"
DEFAULT_PROVIDER_NAME = os.getenv("YUANTUS_PACT_PROVIDER_NAME", "YuantusPLM")
DEFAULT_HOST = os.getenv("YUANTUS_PACT_HOST", "localhost")


def _pact_dir() -> Path:
    return Path(os.getenv("YUANTUS_PACT_DIR", str(DEFAULT_PACT_DIR))).resolve()


def _available_pact_files(pact_dir: Path) -> list[Path]:
    return sorted(path for path in pact_dir.glob("*.json") if path.is_file())


def _find_free_port(host: str = DEFAULT_HOST) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def _provider_state_handler(
    state: str,
    action: str,
    parameters: dict[str, Any] | None,
) -> None:
    """
    Provider state handler.

    We still pre-seed all required data once at the top of the test
    (see `_seed_pact_fixtures`) rather than seeding per-state. The handler
    therefore stays a no-op; the state names exist for documentation and
    for future work where some interactions may need per-state isolation.
    """

    _ = (state, action, parameters)
    return None


# ---------------------------------------------------------------------------
# Test database isolation
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _isolated_test_database():
    """
    Spin up an ephemeral SQLite database scoped to a tempdir, and patch all
    yuantus globals so the FastAPI app's lifespan and request handlers use it.

    On exit, restore the original env vars / globals and delete the tempdir.

    Why this is necessary:
      - `yuantus.database.engine` is created at module import time from the
        process-wide DATABASE_URL. Setting an env var after the import has
        no effect on that already-bound engine. We have to reassign the
        module-level globals after changing the env var.
      - `yuantus.security.auth.database` caches its engine via _engine /
        _sessionmaker globals; we have to reset those too.
      - `get_settings` is `@lru_cache`d, so the cache must be cleared.
      - We force `TENANCY_MODE=single` so the verifier does not need to
        understand multi-tenant DB routing.
    """
    tmpdir = tempfile.mkdtemp(prefix="yuantus_pact_")
    db_path = os.path.join(tmpdir, "pact_meta.db")
    identity_db_path = os.path.join(tmpdir, "pact_identity.db")

    # Settings uses env_prefix="YUANTUS_", so all overrides MUST use that
    # prefix. Without the prefix the values are silently ignored and the
    # .env file's defaults (db-per-tenant-org, yuantus_mt_skip.db, ...) win.
    saved_env = {
        key: os.environ.get(key)
        for key in (
            "YUANTUS_DATABASE_URL",
            "YUANTUS_IDENTITY_DATABASE_URL",
            "YUANTUS_TENANCY_MODE",
            "YUANTUS_ENVIRONMENT",
            "YUANTUS_SCHEMA_MODE",
            "YUANTUS_AUTH_MODE",
        )
    }
    os.environ["YUANTUS_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["YUANTUS_IDENTITY_DATABASE_URL"] = f"sqlite:///{identity_db_path}"
    os.environ["YUANTUS_TENANCY_MODE"] = "single"
    os.environ["YUANTUS_ENVIRONMENT"] = "dev"
    os.environ["YUANTUS_SCHEMA_MODE"] = "create_all"
    os.environ["YUANTUS_AUTH_MODE"] = "optional"

    # Clear cached settings so the new env vars take effect.
    from yuantus.config import get_settings
    get_settings.cache_clear()

    # Reset the module-level engine in yuantus.database. The default
    # `engine` was created at import time from whatever DATABASE_URL was
    # then. Now we rebuild it against the new tempdir.
    import yuantus.database as db_mod

    saved_db_engine = db_mod.engine
    saved_db_sessionlocal = db_mod.SessionLocal
    saved_tenant_engines = dict(db_mod._tenant_engines)
    saved_tenant_sessions = dict(db_mod._tenant_sessions)
    saved_tenant_init_done = set(db_mod._tenant_init_done)

    db_mod.engine = db_mod.create_db_engine()
    db_mod.SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=db_mod.engine,
    )
    db_mod._tenant_engines.clear()
    db_mod._tenant_sessions.clear()
    db_mod._tenant_init_done.clear()

    # Reset the identity DB cache so init_identity_db rebuilds against the
    # new IDENTITY_DATABASE_URL.
    import yuantus.security.auth.database as id_mod

    saved_id_engine = id_mod._engine
    saved_id_sessionmaker = id_mod._sessionmaker
    saved_id_engine_url = id_mod._engine_url
    id_mod._engine = None
    id_mod._sessionmaker = None
    id_mod._engine_url = None

    try:
        yield {
            "tmpdir": tmpdir,
            "db_path": db_path,
            "identity_db_path": identity_db_path,
        }
    finally:
        # Restore yuantus.database globals
        db_mod.engine = saved_db_engine
        db_mod.SessionLocal = saved_db_sessionlocal
        db_mod._tenant_engines.clear()
        db_mod._tenant_engines.update(saved_tenant_engines)
        db_mod._tenant_sessions.clear()
        db_mod._tenant_sessions.update(saved_tenant_sessions)
        db_mod._tenant_init_done.clear()
        db_mod._tenant_init_done.update(saved_tenant_init_done)

        # Restore identity DB
        id_mod._engine = saved_id_engine
        id_mod._sessionmaker = saved_id_sessionmaker
        id_mod._engine_url = saved_id_engine_url

        # Restore env vars
        for key, value in saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        get_settings.cache_clear()

        # Cleanup tempdir
        shutil.rmtree(tmpdir, ignore_errors=True)


def _wait_for_ready(
    health_url: str,
    thread: threading.Thread,
    thread_exception: dict[str, BaseException],
    deadline: float,
) -> None:
    """
    Poll the provider's /api/v1/health until it responds 200, the thread
    dies, or the deadline expires.

    Only readiness-probe exceptions (requests / network) are caught here.
    Anything else propagates.
    """
    last_error: Exception | None = None
    while time.time() < deadline:
        if not thread.is_alive():
            cause = thread_exception.get("error")
            if cause is not None:
                raise RuntimeError(
                    f"Pact provider server crashed during startup: "
                    f"{type(cause).__name__}: {cause}"
                ) from cause
            raise RuntimeError(
                "Pact provider server thread exited cleanly before becoming "
                "ready (uvicorn returned without binding); inspect lifespan "
                "startup hooks in yuantus.api.app._lifespan."
            )
        try:
            response = requests.get(health_url, timeout=0.5)
            if response.ok:
                return
            last_error = RuntimeError(
                f"health endpoint returned {response.status_code}"
            )
        except requests.RequestException as exc:
            last_error = exc
        time.sleep(0.1)

    raise RuntimeError(
        f"Pact provider server did not become ready at {health_url}"
    ) from last_error


# ---------------------------------------------------------------------------
# Test data seeding
# ---------------------------------------------------------------------------


# Constants used by both the pact JSON examples and the seed function. The
# pact request bodies hard-code these values, so seed must match exactly.
PACT_TENANT_ID = "tenant-1"
PACT_USERNAME = "metasheet-svc"
PACT_PASSWORD = "secret"
PACT_ITEM_TYPE = "Part"
PACT_DOCUMENT_ITEM_TYPE = "Document"
PACT_ITEM_ID_PRIMARY = "01H000000000000000000000P1"
PACT_ITEM_ID_SECONDARY = "01H000000000000000000000P2"
PACT_BOM_RELATIONSHIP_TYPE = "Part BOM"
PACT_DOCUMENT_RELATIONSHIP_TYPE = "Document Part"
PACT_DOCUMENT_ID_PRIMARY = "01H000000000000000000000D1"
PACT_DOCUMENT_REL_ID_PRIMARY = "01H000000000000000000000R2"
PACT_FILE_ID_PRIMARY = "01H000000000000000000000F1"
PACT_ITEM_FILE_ID_PRIMARY = "01H000000000000000000000A1"
PACT_ECO_STAGE_ID_HISTORY = "01H000000000000000000000S1"
PACT_ECO_STAGE_ID_APPROVE = "01H000000000000000000000S2"
PACT_ECO_STAGE_ID_REJECT = "01H000000000000000000000S3"
PACT_ECO_ID_HISTORY = "01H000000000000000000000E1"
PACT_ECO_ID_APPROVE = "01H000000000000000000000E2"
PACT_ECO_ID_REJECT = "01H000000000000000000000E3"
PACT_APPROVAL_ID_HISTORY = "01H000000000000000000000H1"


def _seed_pact_fixtures() -> None:
    """
    Pre-seed the isolated test databases with everything every Wave 1 P0
    interaction needs. Called once after the FastAPI app has been created
    but before the server thread starts handling requests.

    Wave 1.5 / 2 milestones:
      - M2: identity tenant + user for /auth/login
      - M3: ItemType('Part') + Item for /search and /aml/apply
      - M4: ItemType('Part BOM') + child Item + BOM relationship for /bom/{id}/tree
      - M5: second comparable Item for /bom/compare
      - M6: FileContainer + ItemFile for /file/item and /file/{id}
      - M7: ItemType('Document') + ItemType('Document Part') + relation for /aml/query expand
      - M8: ECO stages + ECO records for /eco/{id}/approvals|approve|reject
    """
    _seed_identity_user()
    _seed_meta_engine_data()


def _seed_meta_engine_data() -> None:
    """
    Seed the meta engine database with the ItemType + Item rows the pact
    interactions need. Uses direct SQLAlchemy writes to bypass the AML
    engine's permission/lifecycle/validation pipeline — those subsystems
    are not the target of the pact contract test, the field shapes are.
    """
    import sys
    import uuid
    import yuantus.database as db_mod
    from yuantus.database import init_db
    from yuantus.meta_engine.models.eco import ECO, ECOApproval, ECOStage
    from yuantus.meta_engine.models.file import FileContainer, ItemFile
    from yuantus.meta_engine.models.item import Item
    from yuantus.meta_engine.models.meta_schema import ItemType
    from yuantus.security.rbac.models import RBACUser

    sys.stderr.write(
        f"[seed] db_mod.engine.url={db_mod.engine.url}\n"
    )
    init_db(create_tables=True, bind_engine=db_mod.engine)

    # Use the module-level SessionLocal, which we reassigned in
    # _isolated_test_database to bind to the temp DB.
    #
    # Seed in two phases to avoid SQLAlchemy ORM flush-ordering issues:
    # the Item model's circular relationships (current_version_id,
    # source_id, related_id) confuse the topological sorter, so we
    # commit ItemTypes first, then Items in a second session.

    # Phase A: create ItemTypes
    with db_mod.SessionLocal() as session:
        if session.get(ItemType, PACT_ITEM_TYPE) is None:
            session.add(
                ItemType(
                    id=PACT_ITEM_TYPE,
                    label="Part",
                    is_relationship=False,
                    is_versionable=True,
                    properties_schema={},
                    methods={},
                )
            )
        if session.get(ItemType, PACT_BOM_RELATIONSHIP_TYPE) is None:
            session.add(
                ItemType(
                    id=PACT_BOM_RELATIONSHIP_TYPE,
                    label="Part BOM",
                    is_relationship=True,
                    is_versionable=False,
                    source_item_type_id=PACT_ITEM_TYPE,
                    related_item_type_id=PACT_ITEM_TYPE,
                    properties_schema={},
                    methods={},
                )
            )
        if session.get(ItemType, PACT_DOCUMENT_ITEM_TYPE) is None:
            session.add(
                ItemType(
                    id=PACT_DOCUMENT_ITEM_TYPE,
                    label="Document",
                    is_relationship=False,
                    is_versionable=True,
                    properties_schema={},
                    methods={},
                )
            )
        if session.get(ItemType, PACT_DOCUMENT_RELATIONSHIP_TYPE) is None:
            session.add(
                ItemType(
                    id=PACT_DOCUMENT_RELATIONSHIP_TYPE,
                    label="Document Part",
                    is_relationship=True,
                    is_versionable=False,
                    source_item_type_id=PACT_ITEM_TYPE,
                    related_item_type_id=PACT_DOCUMENT_ITEM_TYPE,
                    properties_schema={},
                    methods={},
                )
            )
        session.commit()
        sys.stderr.write("[seed] ItemTypes committed\n")

    # Phase B: create Items (parent, child, related Document, relationships)
    with db_mod.SessionLocal() as session:
        if session.get(Item, PACT_ITEM_ID_PRIMARY) is None:
            session.add(
                Item(
                    id=PACT_ITEM_ID_PRIMARY,
                    item_type_id=PACT_ITEM_TYPE,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Released",
                    is_versionable=True,
                    properties={
                        "item_number": "P-0001",
                        "name": "Mounting Bracket",
                        "description": "Steel mounting bracket",
                    },
                )
            )
        if session.get(Item, PACT_ITEM_ID_SECONDARY) is None:
            session.add(
                Item(
                    id=PACT_ITEM_ID_SECONDARY,
                    item_type_id=PACT_ITEM_TYPE,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Released",
                    is_versionable=True,
                    properties={
                        "item_number": "P-0002",
                        "name": "Bolt M6",
                    },
                )
            )
        if session.get(Item, PACT_DOCUMENT_ID_PRIMARY) is None:
            session.add(
                Item(
                    id=PACT_DOCUMENT_ID_PRIMARY,
                    item_type_id=PACT_DOCUMENT_ITEM_TYPE,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Draft",
                    is_versionable=True,
                    properties={
                        "item_number": "DOC-0001",
                        "doc_number": "DOC-0001",
                        "number": "DOC-0001",
                        "name": "Mounting Bracket Drawing",
                        "current_version_id": "VER-0001",
                        "document_type": "drawing",
                    },
                )
            )
        # BOM relationship: P1 → P2
        bom_rel_id = "01H000000000000000000000R1"
        if session.get(Item, bom_rel_id) is None:
            session.add(
                Item(
                    id=bom_rel_id,
                    item_type_id=PACT_BOM_RELATIONSHIP_TYPE,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Released",
                    is_versionable=False,
                    source_id=PACT_ITEM_ID_PRIMARY,
                    related_id=PACT_ITEM_ID_SECONDARY,
                    properties={
                        "quantity": 4,
                        "uom": "ea",
                        "find_num": "10",
                        "refdes": "B1",
                    },
                )
            )
        if session.get(Item, PACT_DOCUMENT_REL_ID_PRIMARY) is None:
            session.add(
                Item(
                    id=PACT_DOCUMENT_REL_ID_PRIMARY,
                    item_type_id=PACT_DOCUMENT_RELATIONSHIP_TYPE,
                    config_id=str(uuid.uuid4()),
                    generation=1,
                    is_current=True,
                    state="Released",
                    is_versionable=False,
                    source_id=PACT_ITEM_ID_PRIMARY,
                    related_id=PACT_DOCUMENT_ID_PRIMARY,
                    properties={
                        "role": "related_document",
                        "quantity": 1,
                        "uom": "ea",
                        "find_num": "DOC-10",
                        "refdes": "DOC1",
                    },
                )
            )
        session.commit()
        sys.stderr.write("[seed] Items + relationships committed\n")

    # Phase C: create attached file + item file link
    with db_mod.SessionLocal() as session:
        if session.get(FileContainer, PACT_FILE_ID_PRIMARY) is None:
            session.add(
                FileContainer(
                    id=PACT_FILE_ID_PRIMARY,
                    filename="mounting-bracket-drawing.pdf",
                    file_type="pdf",
                    mime_type="application/pdf",
                    file_size=2048,
                    author=PACT_USERNAME,
                    source_system="yuantus",
                    source_version="v1",
                    document_version="A",
                    checksum="sha256-demo-file-1",
                    system_path="demo/files/mounting-bracket-drawing.pdf",
                    document_type="drawing",
                    is_native_cad=False,
                    preview_path="demo/previews/mounting-bracket-drawing.png",
                    conversion_status="pending",
                )
            )
        if session.get(ItemFile, PACT_ITEM_FILE_ID_PRIMARY) is None:
            session.add(
                ItemFile(
                    id=PACT_ITEM_FILE_ID_PRIMARY,
                    item_id=PACT_ITEM_ID_PRIMARY,
                    file_id=PACT_FILE_ID_PRIMARY,
                    file_role="primary",
                    sequence=1,
                    description="Primary manufacturing drawing",
                )
            )
        session.commit()
        sys.stderr.write("[seed] Files + attachments committed\n")

    # Phase D: create approval actor, ECO stages, ECO rows, and one history row
    with db_mod.SessionLocal() as session:
        if session.get(RBACUser, 1) is None:
            session.add(
                RBACUser(
                    id=1,
                    user_id=1,
                    username=PACT_USERNAME,
                    email="metasheet-svc@test.local",
                    is_active=True,
                    is_superuser=True,
                )
            )
        if session.get(ECOStage, PACT_ECO_STAGE_ID_HISTORY) is None:
            session.add(
                ECOStage(
                    id=PACT_ECO_STAGE_ID_HISTORY,
                    name="Engineering Review",
                    sequence=10,
                    approval_type="mandatory",
                    approval_roles=None,
                    min_approvals=1,
                    auto_progress=False,
                )
            )
        if session.get(ECOStage, PACT_ECO_STAGE_ID_APPROVE) is None:
            session.add(
                ECOStage(
                    id=PACT_ECO_STAGE_ID_APPROVE,
                    name="Approve Gate",
                    sequence=20,
                    approval_type="mandatory",
                    approval_roles=None,
                    min_approvals=1,
                    auto_progress=False,
                )
            )
        if session.get(ECOStage, PACT_ECO_STAGE_ID_REJECT) is None:
            session.add(
                ECOStage(
                    id=PACT_ECO_STAGE_ID_REJECT,
                    name="Reject Gate",
                    sequence=30,
                    approval_type="mandatory",
                    approval_roles=None,
                    min_approvals=1,
                    auto_progress=False,
                )
            )
        session.commit()

        if session.get(ECO, PACT_ECO_ID_HISTORY) is None:
            session.add(
                ECO(
                    id=PACT_ECO_ID_HISTORY,
                    name="History ECO",
                    eco_type="bom",
                    product_id=PACT_ITEM_ID_PRIMARY,
                    stage_id=PACT_ECO_STAGE_ID_HISTORY,
                    state="progress",
                    priority="normal",
                    created_by_id=1,
                )
            )
        if session.get(ECO, PACT_ECO_ID_APPROVE) is None:
            session.add(
                ECO(
                    id=PACT_ECO_ID_APPROVE,
                    name="Approve ECO",
                    eco_type="bom",
                    product_id=PACT_ITEM_ID_PRIMARY,
                    stage_id=PACT_ECO_STAGE_ID_APPROVE,
                    state="progress",
                    priority="normal",
                    created_by_id=1,
                )
            )
        if session.get(ECO, PACT_ECO_ID_REJECT) is None:
            session.add(
                ECO(
                    id=PACT_ECO_ID_REJECT,
                    name="Reject ECO",
                    eco_type="bom",
                    product_id=PACT_ITEM_ID_PRIMARY,
                    stage_id=PACT_ECO_STAGE_ID_REJECT,
                    state="progress",
                    priority="normal",
                    created_by_id=1,
                )
            )
        if session.get(ECOApproval, PACT_APPROVAL_ID_HISTORY) is None:
            session.add(
                ECOApproval(
                    id=PACT_APPROVAL_ID_HISTORY,
                    eco_id=PACT_ECO_ID_HISTORY,
                    stage_id=PACT_ECO_STAGE_ID_HISTORY,
                    approval_type="mandatory",
                    required_role="engineer",
                    user_id=1,
                    status="pending",
                    comment="Waiting for engineering review",
                )
            )
        session.commit()
        sys.stderr.write("[seed] ECO approvals committed\n")


def _seed_identity_user() -> None:
    """Create the test tenant and user that the auth/login pact uses."""
    from yuantus.security.auth.database import (
        get_identity_db_session,
        init_identity_db,
    )
    from yuantus.security.auth.service import AuthService

    init_identity_db(create_tables=True)

    with get_identity_db_session() as session:
        service = AuthService(session)
        service.ensure_tenant(PACT_TENANT_ID)
        # create_user raises if the user already exists; that's fine in a
        # fresh isolated DB but we guard with a query in case of re-entry.
        from yuantus.security.auth.models import AuthUser

        existing = (
            session.query(AuthUser)
            .filter(
                AuthUser.tenant_id == PACT_TENANT_ID,
                AuthUser.username == PACT_USERNAME,
            )
            .first()
        )
        if existing is None:
            service.create_user(
                tenant_id=PACT_TENANT_ID,
                username=PACT_USERNAME,
                password=PACT_PASSWORD,
                email="metasheet-svc@test.local",
                is_superuser=True,
            )


def _override_current_user(app) -> None:
    """
    Bypass JWT authentication for non-login endpoints by injecting a fake
    superuser via FastAPI dependency overrides. The actual /auth/login
    endpoint is unaffected because it does not depend on get_current_user.
    """
    from yuantus.api.dependencies.auth import (
        CurrentUser,
        get_current_user,
        get_current_user_id_optional,
        get_current_user_optional,
    )

    fake_user = CurrentUser(
        id=1,
        tenant_id=PACT_TENANT_ID,
        org_id="org-1",
        username=PACT_USERNAME,
        email="metasheet-svc@test.local",
        roles=["admin", "superuser"],
        is_superuser=True,
    )

    def _override():
        return fake_user

    app.dependency_overrides[get_current_user] = _override
    app.dependency_overrides[get_current_user_optional] = _override
    app.dependency_overrides[get_current_user_id_optional] = lambda: fake_user.id


@contextlib.contextmanager
def _running_provider(base_host: str = DEFAULT_HOST):
    # Import lazily so that _isolated_test_database has already overridden
    # DATABASE_URL / IDENTITY_DATABASE_URL by the time create_app() runs.
    from yuantus.api.app import create_app

    port = _find_free_port(base_host)
    app = create_app()
    _seed_pact_fixtures()
    _override_current_user(app)
    config = uvicorn.Config(app, host=base_host, port=port, log_level="error")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None  # type: ignore[assignment]

    # Wrap server.run() so any exception inside the thread is captured and
    # surfaced through the readiness loop, instead of disappearing into the
    # generic "thread is not alive" message.
    thread_exception: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            server.run()
        except BaseException as exc:  # noqa: BLE001 - we re-raise via dict
            thread_exception["error"] = exc
            raise

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()

    base_url = f"http://{base_host}:{port}"
    health_url = f"{base_url}/api/v1/health"
    deadline = time.time() + 15.0

    try:
        # Phase 1: wait until the server is ready. Only readiness errors are
        # caught here; the test body's exceptions are NOT swallowed.
        _wait_for_ready(health_url, thread, thread_exception, deadline)

        # Phase 2: hand the live base_url to the test. Any exception raised by
        # the test body propagates normally — the finally below still runs.
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=10.0)


def test_yuantus_provider_verifies_local_pacts():
    """
    Verify Yuantus against committed consumer pact files.

    This test intentionally skips when the Pact runtime or pact artifacts are
    not present yet. That lets the repository land the verification skeleton
    before Metasheet publishes the first contract set.

    Reference:
    https://docs.pact.io/implementation_guides/python/docs/provider
    """

    pact = pytest.importorskip(
        "pact",
        reason="Install pact-python to enable provider verification",
    )
    pact_dir = _pact_dir()
    pact_files = _available_pact_files(pact_dir)
    if not pact_files:
        pytest.skip(
            f"No pact files found in {pact_dir}. Expected consumer artifacts such as "
            "'metasheet2-yuantus-plm.json'."
        )

    # Add each pact file individually rather than the whole directory.
    # `.add_source(directory)` would attempt to parse every file in the
    # directory (including README.md) and report a Pact JSON parse error.
    verifier = pact.Verifier(DEFAULT_PROVIDER_NAME)
    for path in pact_files:
        verifier = verifier.add_source(str(path))
    verifier = verifier.state_handler(_provider_state_handler, teardown=True)

    with _isolated_test_database():
        with _running_provider() as base_url:
            verifier = verifier.add_transport(url=base_url)
            verifier.verify()
