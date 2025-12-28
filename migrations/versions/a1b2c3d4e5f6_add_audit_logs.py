"""add audit logs

Revision ID: a1b2c3d4e5f6
Revises: e5c1f9a4b7d2
Create Date: 2025-12-20 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "e5c1f9a4b7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "audit_logs" not in inspector.get_table_names():
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.String(length=36), nullable=False),
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
            sa.PrimaryKeyConstraint("id"),
        )

    existing_indexes = {
        ix.get("name") for ix in inspector.get_indexes("audit_logs")
    }
    index_org = op.f("ix_audit_logs_org_id")
    if index_org not in existing_indexes:
        op.create_index(index_org, "audit_logs", ["org_id"], unique=False)
    index_tenant = op.f("ix_audit_logs_tenant_id")
    if index_tenant not in existing_indexes:
        op.create_index(index_tenant, "audit_logs", ["tenant_id"], unique=False)
    index_user = op.f("ix_audit_logs_user_id")
    if index_user not in existing_indexes:
        op.create_index(index_user, "audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "audit_logs" not in inspector.get_table_names():
        return
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_org_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
