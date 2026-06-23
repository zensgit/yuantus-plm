"""Lifecycle promote() records FAILED / denied / blocked / aborted attempts (T2, all-attempts).

Per the all-attempts taskbook (#846): each B-class failure path writes a **best-effort** audit row
through a SEPARATE ``get_db_session()`` that commits independently — so the row survives the caller
rolling back the failed attempt (``promote_op`` raises on a failed ``PromoteResult`` → the AML apply
transaction never commits → a same-session row would vanish). ``outcome`` is low-cardinality
(``denied`` / ``blocked`` / ``aborted`` / ``failed``) with the exact reason in
``properties.reason_code``; never a raw exception. The item-scoped read stays success-only; failures
surface only on the forensic route.

NOTE on rollback-survival fidelity: these tests run on in-memory sqlite + ``StaticPool`` (a SINGLE
shared connection), so they **cannot** prove TRUE cross-connection rollback-survival — that is
Postgres-only / integration-verified. What they prove faithfully here: each failure path writes the
right ``outcome`` / ``reason_code``; the attempt row is written via ``get_db_session()`` (redirected
to the test DB) and **not** added to ``self.session`` (structural); the write is best-effort (a
raising audit never changes the ``PromoteResult``); and the item-scoped read excludes non-success.
"""
from __future__ import annotations

import contextlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import yuantus.database as ydb
from yuantus.meta_engine.lifecycle.hooks import HookType, hook_registry
from yuantus.meta_engine.lifecycle.models import (
    LifecycleMap,
    LifecycleState,
    LifecycleTransition,
    LifecycleTransitionHistory,
)
from yuantus.meta_engine.lifecycle.service import LifecycleService
from yuantus.meta_engine.models.item import Item
from yuantus.meta_engine.models.meta_schema import ItemType
from yuantus.models import user as _user  # noqa: F401 - registers the 'users' table (FK target)
from yuantus.models.base import Base

_ITEM_TYPE = "AA-Part"


@pytest.fixture()
def env(monkeypatch):
    from yuantus.meta_engine.bootstrap import import_all_models

    import_all_models()
    eng = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng, expire_on_commit=False)

    # The failure-write helper opens a SEPARATE get_db_session() that commits independently.
    # Redirect it to THIS test engine (shared StaticPool connection) so the row is observable.
    @contextlib.contextmanager
    def _audit_session():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    monkeypatch.setattr(ydb, "get_db_session", _audit_session)

    s = SessionLocal()
    s.add(LifecycleMap(id="m", name="L"))
    s.add(LifecycleState(id="s_draft", name="Draft", lifecycle_map_id="m", is_start_state=True))
    s.add(
        LifecycleState(
            id="s_rel", name="Released", lifecycle_map_id="m", is_released=True,
            default_permission_id="perm_rel",
        )
    )
    # An ISOLATED state with no transition from Draft (drives the transition_missing path).
    s.add(LifecycleState(id="s_obs", name="Obsolete", lifecycle_map_id="m"))
    s.add(LifecycleTransition(id="t", lifecycle_map_id="m", from_state_id="s_draft", to_state_id="s_rel"))
    s.add(ItemType(id=_ITEM_TYPE, label="AA Part", is_versionable=False, lifecycle_map_id="m"))
    s.commit()
    try:
        yield s, SessionLocal
    finally:
        s.close()


def _draft_item(session, iid="i1"):
    item = Item(
        id=iid, config_id=iid, item_type_id=_ITEM_TYPE, state="Draft", current_state="s_draft",
        permission_id="perm_draft", is_versionable=False, is_current=True, properties={},
    )
    session.add(item)
    session.commit()
    return item


@contextlib.contextmanager
def _abort_hook(hook_type):
    """Register an aborting hook at ``hook_type`` for the test item type; restore on exit."""
    key = f"{_ITEM_TYPE}:{hook_type.value}"
    before = list(hook_registry._hooks.get(key, []))

    def _abort(ctx):
        ctx.abort = True
        ctx.abort_reason = "test abort"

    hook_registry.register(_ITEM_TYPE, hook_type, _abort)
    try:
        yield
    finally:
        hook_registry._hooks[key] = before


def _attempts(SessionLocal, item_id):
    """Read the attempt rows the helper committed to the (separate) audit session's DB."""
    s = SessionLocal()
    try:
        return (
            s.query(LifecycleTransitionHistory)
            .filter(LifecycleTransitionHistory.item_id == item_id)
            .all()
        )
    finally:
        s.close()


# -- per-path outcome ---------------------------------------------------------------------------
def test_target_state_not_found_records_denied(env):
    s, SessionLocal = env
    item = _draft_item(s)
    res = LifecycleService(s).promote(item, "NoSuchState", user_id=7)
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    r = rows[0]
    assert r.outcome == "denied" and r.properties["reason_code"] == "target_state_not_found"
    assert r.actor_user_id == 7 and r.from_state_name == "Draft" and r.to_state_name == "NoSuchState"


def test_transition_missing_records_denied(env):
    s, SessionLocal = env
    item = _draft_item(s)
    res = LifecycleService(s).promote(item, "Obsolete", user_id=7)  # no Draft->Obsolete transition
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "denied" and rows[0].properties["reason_code"] == "transition_missing"
    assert rows[0].to_state_id == "s_obs"


def test_before_transition_abort_records_aborted(env):
    s, SessionLocal = env
    item = _draft_item(s)
    with _abort_hook(HookType.BEFORE_TRANSITION):
        res = LifecycleService(s).promote(item, "Released", user_id=7)
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "aborted" and rows[0].properties["reason_code"] == "before_transition_aborted"


def test_on_exit_abort_records_aborted(env):
    s, SessionLocal = env
    item = _draft_item(s)
    with _abort_hook(HookType.ON_EXIT_STATE):
        res = LifecycleService(s).promote(item, "Released", user_id=7)
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "aborted" and rows[0].properties["reason_code"] == "on_exit_aborted"


def test_on_enter_abort_records_aborted_and_rolled_back(env):
    s, SessionLocal = env
    item = _draft_item(s)
    with _abort_hook(HookType.ON_ENTER_STATE):
        res = LifecycleService(s).promote(item, "Released", user_id=7)
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "aborted" and rows[0].properties["reason_code"] == "on_enter_aborted"
    assert rows[0].properties.get("rolled_back") is True
    assert rows[0].to_state_id == "s_rel"  # attempted target recorded


# -- structural: attempt rides the SEPARATE session, never self.session -------------------------
def test_attempt_not_added_to_caller_session(env):
    # The load-bearing structural guarantee (sqlite can't prove cross-connection, so assert this):
    # a failed promote must NOT leave an attempt row pending on the CALLER's session — it goes via
    # the independent audit session. (If it rode self.session, the caller's rollback would drop it.)
    s, SessionLocal = env
    item = _draft_item(s)
    LifecycleService(s).promote(item, "NoSuchState", user_id=7)
    pending = [o for o in s.new if isinstance(o, LifecycleTransitionHistory)]
    assert pending == []  # nothing queued on the caller session
    s.rollback()  # the caller rolls back the failed attempt...
    assert len(_attempts(SessionLocal, item.id)) == 1  # ...the independently-committed row remains


# -- best-effort: a failing audit write never changes the PromoteResult or raises ---------------
def test_best_effort_audit_failure_never_breaks_promote(env, monkeypatch):
    s, _ = env
    item = _draft_item(s)

    @contextlib.contextmanager
    def _boom():
        raise RuntimeError("audit session boom")
        yield  # pragma: no cover

    monkeypatch.setattr(ydb, "get_db_session", _boom)
    # The promote still fails for its OWN reason (bad target), and the audit explosion is swallowed.
    res = LifecycleService(s).promote(item, "NoSuchState", user_id=7)
    assert res.success is False and "NoSuchState" in (res.error or "")


# -- read surface: item-scoped is success-only; forensic sees all -------------------------------
def test_item_read_filters_to_success_only(env):
    s, _ = env
    s.add(LifecycleTransitionHistory(item_id="X", outcome="success"))
    s.add(
        LifecycleTransitionHistory(
            item_id="X", outcome="denied", properties={"reason_code": "permission_denied"}
        )
    )
    s.commit()
    svc = LifecycleService(s)
    assert {r.outcome for r in svc.get_transition_history("X", success_only=True)} == {"success"}
    assert {r.outcome for r in svc.get_transition_history("X", success_only=False)} == {
        "success",
        "denied",
    }


# -- the exception path: "failed" outcome, and NEVER a raw exception in the audit (Q5) ----------
def test_version_release_failure_records_failed_without_raw_exception(env, monkeypatch):
    # The version-release path splices str(e) into PromoteResult.error; the AUDIT must record only
    # the bounded reason_code + a generic public_message, NEVER the raw exception text.
    s, SessionLocal = env
    item = Item(
        id="iv", config_id="iv", item_type_id=_ITEM_TYPE, state="Draft", current_state="s_draft",
        permission_id="perm_draft", is_versionable=True, is_current=True, properties={},
    )
    s.add(item)
    s.commit()

    from yuantus.meta_engine.version import service as _vsvc

    monkeypatch.setattr(_vsvc.VersionService, "create_initial_version", lambda *a, **k: None)
    monkeypatch.setattr(
        _vsvc.VersionService,
        "release",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("SECRET-INTERNAL-version-detail")),
    )
    res = LifecycleService(s).promote(item, "Released", user_id=7)
    assert res.success is False
    rows = _attempts(SessionLocal, "iv")
    assert len(rows) == 1
    r = rows[0]
    assert r.outcome == "failed" and r.properties["reason_code"] == "version_release_failed"
    assert r.properties.get("rolled_back") is True
    assert r.properties.get("public_message") == "version release failed"
    import json

    assert "SECRET-INTERNAL" not in json.dumps(r.properties)  # raw exception never leaks


# -- the role-gate denial branch (role_allowed_id) ----------------------------------------------
def test_actor_missing_records_denied(env):
    s, SessionLocal = env
    from yuantus.security.rbac.models import RBACRole

    s.add(RBACRole(id=1, name="approver"))
    s.get(LifecycleTransition, "t").role_allowed_id = 1  # role-gate Draft->Released
    s.commit()
    item = _draft_item(s)
    res = LifecycleService(s).promote(item, "Released", user_id=999)  # no RBACUser 999
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "denied" and rows[0].properties["reason_code"] == "actor_missing"


def test_permission_denied_records_denied(env):
    s, SessionLocal = env
    from yuantus.security.rbac.models import RBACRole, RBACUser

    s.add(RBACRole(id=1, name="approver"))
    s.add(RBACUser(id=5, user_id=5, username="nobody", is_superuser=False))  # exists, but no roles
    s.get(LifecycleTransition, "t").role_allowed_id = 1
    s.commit()
    item = _draft_item(s)
    res = LifecycleService(s).promote(item, "Released", user_id=5)
    assert res.success is False
    rows = _attempts(SessionLocal, item.id)
    assert len(rows) == 1
    assert rows[0].outcome == "denied" and rows[0].properties["reason_code"] == "permission_denied"
