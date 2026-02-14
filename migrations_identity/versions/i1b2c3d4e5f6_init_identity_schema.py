"""Init identity schema (auth + audit).

Revision ID: i1b2c3d4e5f6
Revises:
Create Date: 2026-02-14

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_tenants",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "auth_organizations",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["auth_tenants.id"]),
        sa.UniqueConstraint("tenant_id", "id", name="uq_tenant_org"),
    )
    op.create_index(
        "ix_auth_organizations_tenant_id", "auth_organizations", ["tenant_id"]
    )

    op.create_table(
        "auth_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["auth_tenants.id"]),
        sa.UniqueConstraint("tenant_id", "username", name="uq_auth_user_tenant_username"),
    )
    op.create_index("ix_auth_users_tenant_id", "auth_users", ["tenant_id"])

    op.create_table(
        "auth_credentials",
        sa.Column("user_id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("password_hash", sa.String(length=500), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "auth_org_memberships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("roles", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["auth_tenants.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["auth_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["auth_users.id"]),
        sa.UniqueConstraint("tenant_id", "org_id", "user_id", name="uq_auth_membership"),
    )
    op.create_index(
        "ix_auth_org_memberships_tenant_id", "auth_org_memberships", ["tenant_id"]
    )
    op.create_index(
        "ix_auth_org_memberships_org_id", "auth_org_memberships", ["org_id"]
    )
    op.create_index(
        "ix_auth_org_memberships_user_id", "auth_org_memberships", ["user_id"]
    )

    op.create_table(
        "auth_tenant_quotas",
        sa.Column("tenant_id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=True),
        sa.Column("max_orgs", sa.Integer(), nullable=True),
        sa.Column("max_files", sa.Integer(), nullable=True),
        sa.Column("max_storage_bytes", sa.BigInteger(), nullable=True),
        sa.Column("max_active_jobs", sa.Integer(), nullable=True),
        sa.Column("max_processing_jobs", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["auth_tenants.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("org_id", sa.String(length=64), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_org_id", "audit_logs", ["org_id"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("auth_tenant_quotas")

    op.drop_index("ix_auth_org_memberships_user_id", table_name="auth_org_memberships")
    op.drop_index("ix_auth_org_memberships_org_id", table_name="auth_org_memberships")
    op.drop_index(
        "ix_auth_org_memberships_tenant_id", table_name="auth_org_memberships"
    )
    op.drop_table("auth_org_memberships")

    op.drop_table("auth_credentials")

    op.drop_index("ix_auth_users_tenant_id", table_name="auth_users")
    op.drop_table("auth_users")

    op.drop_index("ix_auth_organizations_tenant_id", table_name="auth_organizations")
    op.drop_table("auth_organizations")

    op.drop_table("auth_tenants")

