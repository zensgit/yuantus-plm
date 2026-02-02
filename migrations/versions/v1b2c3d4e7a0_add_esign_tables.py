"""add electronic signature tables

Revision ID: v1b2c3d4e7a0
Revises: u1b2c3d4e6a9
Create Date: 2026-02-01 23:40:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v1b2c3d4e7a0"
down_revision: Union[str, None] = "u1b2c3d4e6a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_signing_reasons" not in existing:
        op.create_table(
            "meta_signing_reasons",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("code", sa.String(), nullable=False, unique=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("meaning", sa.String(), nullable=False, server_default="approved"),
            sa.Column("regulatory_reference", sa.String(), nullable=True),
            sa.Column("item_type_id", sa.String(), nullable=True),
            sa.Column("from_state", sa.String(), nullable=True),
            sa.Column("to_state", sa.String(), nullable=True),
            sa.Column("requires_password", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("requires_comment", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["item_type_id"], ["meta_item_types.id"], ondelete="SET NULL"),
        )

    if "meta_electronic_signatures" not in existing:
        op.create_table(
            "meta_electronic_signatures",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("item_id", sa.String(), nullable=False, index=True),
            sa.Column("item_generation", sa.Integer(), nullable=False),
            sa.Column("signer_id", sa.Integer(), nullable=False),
            sa.Column("signer_username", sa.String(), nullable=False),
            sa.Column("signer_full_name", sa.String(), nullable=False),
            sa.Column("reason_id", sa.String(), nullable=True),
            sa.Column("meaning", sa.String(), nullable=False),
            sa.Column("reason_text", sa.String(), nullable=True),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("signed_at", sa.DateTime(), nullable=False),
            sa.Column("signature_hash", sa.String(), nullable=False),
            sa.Column("content_hash", sa.String(), nullable=False),
            sa.Column(
                "client_info",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("client_ip", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="valid"),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_by_id", sa.Integer(), nullable=True),
            sa.Column("revocation_reason", sa.Text(), nullable=True),
            sa.Column("workflow_instance_id", sa.String(), nullable=True),
            sa.Column("workflow_activity_id", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["signer_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["reason_id"], ["meta_signing_reasons.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["revoked_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_signature_manifests" not in existing:
        op.create_table(
            "meta_signature_manifests",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("item_id", sa.String(), nullable=False, index=True),
            sa.Column("item_generation", sa.Integer(), nullable=False),
            sa.Column(
                "required_signatures",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("manifest_hash", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="CASCADE"),
        )

    if "meta_signature_audit_logs" not in existing:
        op.create_table(
            "meta_signature_audit_logs",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("signature_id", sa.String(), nullable=True),
            sa.Column("item_id", sa.String(), nullable=True),
            sa.Column("actor_id", sa.Integer(), nullable=False),
            sa.Column("actor_username", sa.String(), nullable=False),
            sa.Column(
                "details",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.Column("client_ip", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["signature_id"], ["meta_electronic_signatures.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["actor_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "meta_signature_audit_logs" in existing:
        op.drop_table("meta_signature_audit_logs")

    if "meta_signature_manifests" in existing:
        op.drop_table("meta_signature_manifests")

    if "meta_electronic_signatures" in existing:
        op.drop_table("meta_electronic_signatures")

    if "meta_signing_reasons" in existing:
        op.drop_table("meta_signing_reasons")
