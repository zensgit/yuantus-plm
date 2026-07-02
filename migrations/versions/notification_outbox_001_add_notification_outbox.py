"""add durable notification outbox tables

Revision ID: notification_outbox_001
Revises: date_obsolete_corr_001
Create Date: 2026-07-02 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "notification_outbox_001"
down_revision: Union[str, None] = "date_obsolete_corr_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _j() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB, "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_notification_outbox" not in existing:
        op.create_table(
            "meta_notification_outbox",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=True),
            sa.Column("org_id", sa.String(length=64), nullable=True),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("object_type", sa.String(length=120), nullable=True),
            sa.Column("object_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("payload", _j(), nullable=True),
            sa.Column("payload_fingerprint", sa.String(length=128), nullable=False),
            sa.Column("idempotency_key", sa.String(length=128), nullable=False),
            sa.Column("state", sa.String(length=30), nullable=False),
            sa.Column("properties", _j(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "idempotency_key", name="uq_notification_outbox_idempotency_key"
            ),
        )
        op.create_index(
            "ix_meta_notification_outbox_tenant_id",
            "meta_notification_outbox",
            ["tenant_id"],
        )
        op.create_index(
            "ix_meta_notification_outbox_org_id",
            "meta_notification_outbox",
            ["org_id"],
        )
        op.create_index(
            "ix_meta_notification_outbox_event_type",
            "meta_notification_outbox",
            ["event_type"],
        )
        op.create_index(
            "ix_meta_notification_outbox_object_id",
            "meta_notification_outbox",
            ["object_id"],
        )

    existing = set(sa.inspect(bind).get_table_names())
    if "meta_notification_deliveries" not in existing:
        op.create_table(
            "meta_notification_deliveries",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("notification_id", sa.String(), nullable=False),
            sa.Column("tenant_id", sa.String(length=64), nullable=True),
            sa.Column("org_id", sa.String(length=64), nullable=True),
            sa.Column("recipient_user_id", sa.Integer(), nullable=True),
            sa.Column("recipient_key", sa.String(length=200), nullable=False),
            sa.Column("recipient_email", sa.String(length=255), nullable=True),
            sa.Column("channel", sa.String(length=30), nullable=False),
            sa.Column("state", sa.String(length=30), nullable=False),
            sa.Column("reason", sa.String(length=30), nullable=True),
            sa.Column(
                "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
            ),
            sa.Column(
                "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")
            ),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("remote_id", sa.String(), nullable=True),
            sa.Column("payload", _j(), nullable=True),
            sa.Column("properties", _j(), nullable=True),
            sa.Column(
                "next_attempt_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("worker_id", sa.String(), nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(
                ["notification_id"], ["meta_notification_outbox.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["recipient_user_id"], ["rbac_users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "notification_id",
                "recipient_key",
                "channel",
                name="uq_notification_delivery_recipient_channel",
            ),
        )
        op.create_index(
            "ix_meta_notification_deliveries_notification_id",
            "meta_notification_deliveries",
            ["notification_id"],
        )
        op.create_index(
            "ix_meta_notification_deliveries_tenant_id",
            "meta_notification_deliveries",
            ["tenant_id"],
        )
        op.create_index(
            "ix_meta_notification_deliveries_org_id",
            "meta_notification_deliveries",
            ["org_id"],
        )


def downgrade() -> None:
    op.drop_table("meta_notification_deliveries")
    op.drop_table("meta_notification_outbox")
