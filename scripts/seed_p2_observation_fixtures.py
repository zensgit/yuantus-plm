#!/usr/bin/env python3
"""Seed a minimal ECO dataset covering the P2 observation regression scenarios."""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yuantus.meta_engine.bootstrap import import_all_models

import_all_models()

from yuantus.database import get_db_session
from yuantus.meta_engine.models.eco import ECO, ECOApproval, ECOStage, ECOState
from yuantus.security.rbac.models import RBACRole, RBACUser


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the minimal P2 observation ECO fixtures used by shared-dev/local regression."
    )
    parser.add_argument("--tenant", default="tenant-1", help="Tenant id recorded in the manifest.")
    parser.add_argument("--org", default="org-1", help="Org id recorded in the manifest.")
    parser.add_argument("--admin-user-id", type=int, default=1, help="Bootstrap admin RBAC user id.")
    parser.add_argument("--admin-username", default="admin", help="Bootstrap admin username.")
    parser.add_argument("--viewer-user-id", type=int, default=2, help="Bootstrap viewer RBAC user id.")
    parser.add_argument("--viewer-username", default="ops-viewer", help="Bootstrap viewer username.")
    parser.add_argument(
        "--manifest-path",
        default="",
        help="Optional output path for a JSON manifest containing stage/ECO ids.",
    )
    return parser.parse_args()


def ensure_role(session, name: str, display_name: str) -> RBACRole:
    role = session.query(RBACRole).filter_by(name=name).first()
    if role is None:
        role = RBACRole(name=name, display_name=display_name, is_active=True)
        session.add(role)
        session.flush()
    return role


def ensure_role_binding(user: RBACUser | None, role: RBACRole) -> None:
    if user is not None and role not in (user.roles or []):
        user.roles.append(role)


def ensure_rbac_user(
    session,
    *,
    user_id: int,
    username: str,
    is_superuser: bool,
    email: str | None = None,
) -> RBACUser:
    user = session.get(RBACUser, user_id)
    if user is None:
        user = session.query(RBACUser).filter_by(user_id=user_id).first()
    if user is None:
        user = session.query(RBACUser).filter_by(username=username).first()

    if user is None:
        user = RBACUser(
            id=user_id,
            user_id=user_id,
            username=username,
            email=email or f"{username}@example.com",
            is_active=True,
            is_superuser=is_superuser,
        )
        session.add(user)
        session.flush()
        return user

    changed = False
    if user.user_id != user_id:
        user.user_id = user_id
        changed = True
    if user.username != username:
        user.username = username
        changed = True
    if email and user.email != email:
        user.email = email
        changed = True
    if bool(user.is_superuser) != bool(is_superuser):
        user.is_superuser = is_superuser
        changed = True
    if not bool(user.is_active):
        user.is_active = True
        changed = True
    if changed:
        session.add(user)
        session.flush()
    return user


def make_eco(session, *, name: str, stage_id: str, deadline: datetime | None, created_by_id: int) -> ECO:
    eco = ECO(
        id=str(uuid.uuid4()),
        name=name,
        eco_type="bom",
        state=ECOState.PROGRESS.value,
        stage_id=stage_id,
        approval_deadline=deadline,
        created_by_id=created_by_id,
    )
    session.add(eco)
    session.flush()
    return eco


def make_approval(
    session,
    *,
    eco_id: str,
    stage_id: str,
    user_id: int,
    required_role: str | None = None,
) -> ECOApproval:
    approval = ECOApproval(
        id=str(uuid.uuid4()),
        eco_id=eco_id,
        stage_id=stage_id,
        user_id=user_id,
        approval_type="mandatory",
        required_role=required_role,
        status="pending",
    )
    session.add(approval)
    return approval


def write_manifest(path: str, payload: dict[str, object]) -> None:
    if not path:
        return
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    now = datetime.utcnow()

    with get_db_session() as session:
        engineer_role = ensure_role(session, "engineer", "Engineer")
        ops_viewer_role = ensure_role(session, "ops-viewer", "Ops Viewer")

        admin = ensure_rbac_user(
            session,
            user_id=args.admin_user_id,
            username=args.admin_username,
            is_superuser=True,
            email=f"{args.admin_username}@example.com",
        )
        ensure_role_binding(admin, engineer_role)

        viewer = ensure_rbac_user(
            session,
            user_id=args.viewer_user_id,
            username=args.viewer_username,
            is_superuser=False,
            email=f"{args.viewer_username}@example.com",
        )
        ensure_role_binding(viewer, ops_viewer_role)

        review = session.query(ECOStage).filter_by(name="Review").first()
        if review is None:
            review = ECOStage(
                id=str(uuid.uuid4()),
                name="Review",
                sequence=10,
                approval_type="mandatory",
                approval_roles=["engineer"],
                min_approvals=1,
                sla_hours=24,
                auto_progress=False,
            )
            session.add(review)

        specialist = session.query(ECOStage).filter_by(name="SpecialistReview").first()
        if specialist is None:
            specialist = ECOStage(
                id=str(uuid.uuid4()),
                name="SpecialistReview",
                sequence=20,
                approval_type="mandatory",
                approval_roles=["specialist"],
                min_approvals=1,
                sla_hours=24,
                auto_progress=False,
            )
            session.add(specialist)

        session.flush()

        session.query(ECOApproval).delete()
        session.query(ECO).delete()
        session.flush()

        eco_pending = make_eco(
            session,
            name="eco-pending",
            stage_id=review.id,
            deadline=now + timedelta(hours=20),
            created_by_id=args.admin_user_id,
        )
        eco_overdue_admin = make_eco(
            session,
            name="eco-overdue-admin",
            stage_id=review.id,
            deadline=now - timedelta(hours=5),
            created_by_id=args.admin_user_id,
        )
        eco_overdue_ops = make_eco(
            session,
            name="eco-overdue-opsview",
            stage_id=review.id,
            deadline=now - timedelta(hours=3),
            created_by_id=args.admin_user_id,
        )
        eco_specialist = make_eco(
            session,
            name="eco-specialist",
            stage_id=specialist.id,
            deadline=now + timedelta(hours=48),
            created_by_id=args.admin_user_id,
        )

        make_approval(
            session,
            eco_id=eco_pending.id,
            stage_id=review.id,
            user_id=args.admin_user_id,
        )
        make_approval(
            session,
            eco_id=eco_overdue_admin.id,
            stage_id=review.id,
            user_id=args.admin_user_id,
        )
        make_approval(
            session,
            eco_id=eco_overdue_ops.id,
            stage_id=review.id,
            user_id=args.viewer_user_id,
        )

        session.commit()

    manifest = {
        "tenant_id": args.tenant,
        "org_id": args.org,
        "users": {
            "admin": {"user_id": args.admin_user_id, "username": args.admin_username},
            "ops_viewer": {"user_id": args.viewer_user_id, "username": args.viewer_username},
        },
        "stages": {
            "review": {"name": "Review"},
            "specialist_review": {"name": "SpecialistReview"},
        },
        "ecos": {
            "pending": {"name": "eco-pending", "id": eco_pending.id},
            "overdue_admin": {"name": "eco-overdue-admin", "id": eco_overdue_admin.id},
            "overdue_opsview": {"name": "eco-overdue-opsview", "id": eco_overdue_ops.id},
            "specialist": {"name": "eco-specialist", "id": eco_specialist.id},
        },
        "expected_baseline": {
            "pending_count": 1,
            "overdue_count": 2,
            "escalated_count": 0,
            "overdue_not_escalated": 2,
            "escalated_unresolved": 0,
        },
        "expected_after_escalate": {
            "pending_count": 1,
            "overdue_count": 3,
            "escalated_count": 1,
            "overdue_not_escalated": 1,
            "escalated_unresolved": 1,
        },
    }

    write_manifest(args.manifest_path, manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
