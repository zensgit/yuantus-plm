"""add dedup rules and records

Revision ID: r1b2c3d4e6a6
Revises: q1b2c3d4e6a5
Create Date: 2026-01-31 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "r1b2c3d4e6a6"
down_revision: Union[str, None] = "q1b2c3d4e6a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing = set(inspector.get_table_names())

    if "meta_dedup_rules" not in existing:
        op.create_table(
            "meta_dedup_rules",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("item_type_id", sa.String(), nullable=True),
            sa.Column("document_type", sa.String(), nullable=True),
            sa.Column("phash_threshold", sa.Integer(), nullable=False, server_default="10"),
            sa.Column("feature_threshold", sa.Float(), nullable=False, server_default="0.85"),
            sa.Column("combined_threshold", sa.Float(), nullable=False, server_default="0.8"),
            sa.Column("detection_mode", sa.String(), nullable=False, server_default="balanced"),
            sa.Column("auto_create_relationship", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("auto_trigger_workflow", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("workflow_map_id", sa.String(), nullable=True),
            sa.Column(
                "exclude_patterns",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["item_type_id"], ["meta_item_types.id"]),
            sa.ForeignKeyConstraint(["workflow_map_id"], ["meta_workflow_maps.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.UniqueConstraint("name", name="uq_meta_dedup_rule_name"),
        )

    if "meta_dedup_batches" not in existing:
        op.create_table(
            "meta_dedup_batches",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("scope_type", sa.String(), nullable=False, server_default="all"),
            sa.Column(
                "scope_config",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("rule_id", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="queued"),
            sa.Column("total_files", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("processed_files", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("found_similarities", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column(
                "summary",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("created_by_id", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["rule_id"], ["meta_dedup_rules.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
        )

    if "meta_similarity_records" not in existing:
        op.create_table(
            "meta_similarity_records",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("source_file_id", sa.String(), nullable=False),
            sa.Column("target_file_id", sa.String(), nullable=False),
            sa.Column("similarity_score", sa.Float(), nullable=False),
            sa.Column("similarity_type", sa.String(), nullable=True, server_default="visual"),
            sa.Column("detection_method", sa.String(), nullable=True),
            sa.Column(
                "detection_params",
                sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
                nullable=True,
            ),
            sa.Column("status", sa.String(), nullable=False, server_default="pending"),
            sa.Column("reviewed_by_id", sa.Integer(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("review_comment", sa.Text(), nullable=True),
            sa.Column("relationship_item_id", sa.String(), nullable=True),
            sa.Column("batch_id", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["source_file_id"], ["meta_files.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["target_file_id"], ["meta_files.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reviewed_by_id"], ["rbac_users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["relationship_item_id"], ["meta_items.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["batch_id"], ["meta_dedup_batches.id"], ondelete="SET NULL"),
        )

    inspector = sa.inspect(bind)
    indexes = {idx.get("name") for idx in inspector.get_indexes("meta_similarity_records")}
    if "ix_meta_similarity_records_source_file_id" not in indexes:
        op.create_index(
            "ix_meta_similarity_records_source_file_id",
            "meta_similarity_records",
            ["source_file_id"],
        )
    if "ix_meta_similarity_records_target_file_id" not in indexes:
        op.create_index(
            "ix_meta_similarity_records_target_file_id",
            "meta_similarity_records",
            ["target_file_id"],
        )
    if "ix_meta_similarity_records_status" not in indexes:
        op.create_index(
            "ix_meta_similarity_records_status",
            "meta_similarity_records",
            ["status"],
        )
    if "ix_meta_similarity_records_batch_id" not in indexes:
        op.create_index(
            "ix_meta_similarity_records_batch_id",
            "meta_similarity_records",
            ["batch_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing = set(inspector.get_table_names())
    if "meta_similarity_records" in existing:
        indexes = {idx.get("name") for idx in inspector.get_indexes("meta_similarity_records")}
        if "ix_meta_similarity_records_batch_id" in indexes:
            op.drop_index("ix_meta_similarity_records_batch_id", table_name="meta_similarity_records")
        if "ix_meta_similarity_records_status" in indexes:
            op.drop_index("ix_meta_similarity_records_status", table_name="meta_similarity_records")
        if "ix_meta_similarity_records_target_file_id" in indexes:
            op.drop_index("ix_meta_similarity_records_target_file_id", table_name="meta_similarity_records")
        if "ix_meta_similarity_records_source_file_id" in indexes:
            op.drop_index("ix_meta_similarity_records_source_file_id", table_name="meta_similarity_records")
        op.drop_table("meta_similarity_records")

    if "meta_dedup_batches" in existing:
        op.drop_table("meta_dedup_batches")
    if "meta_dedup_rules" in existing:
        op.drop_table("meta_dedup_rules")
