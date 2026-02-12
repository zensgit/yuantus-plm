"""add similarity record unordered pair key

Revision ID: y1b2c3d4e7a3
Revises: x1b2c3d4e7a2
Create Date: 2026-02-12 21:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "y1b2c3d4e7a3"
down_revision: Union[str, None] = "x1b2c3d4e7a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_similarity_records" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_similarity_records")}
    if "pair_key" not in columns:
        op.add_column(
            "meta_similarity_records",
            sa.Column("pair_key", sa.String(length=80), nullable=True),
        )

    # Backfill existing records so the unique index can be created safely.
    # Use lexical comparison across UUID strings; stable across sqlite/postgresql.
    op.execute(
        sa.text(
            """
            UPDATE meta_similarity_records
            SET pair_key = CASE
                WHEN source_file_id < target_file_id THEN source_file_id || '|' || target_file_id
                ELSE target_file_id || '|' || source_file_id
            END
            WHERE pair_key IS NULL OR pair_key = ''
            """
        )
    )

    # Defensive cleanup: if historical duplicates exist (from earlier race conditions), drop
    # extras so we can enforce uniqueness at the DB level. Keep the newest record by created_at.
    op.execute(
        sa.text(
            """
            DELETE FROM meta_similarity_records
            WHERE id IN (
                SELECT id FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY pair_key
                            ORDER BY created_at DESC, id DESC
                        ) AS rn
                    FROM meta_similarity_records
                    WHERE pair_key IS NOT NULL AND pair_key <> ''
                ) t
                WHERE t.rn > 1
            )
            """
        )
    )

    inspector = sa.inspect(bind)
    indexes = {idx.get("name") for idx in inspector.get_indexes("meta_similarity_records")}
    if "uq_meta_similarity_records_pair_key" not in indexes:
        op.create_index(
            "uq_meta_similarity_records_pair_key",
            "meta_similarity_records",
            ["pair_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_similarity_records" not in inspector.get_table_names():
        return

    indexes = {idx.get("name") for idx in inspector.get_indexes("meta_similarity_records")}
    if "uq_meta_similarity_records_pair_key" in indexes:
        op.drop_index(
            "uq_meta_similarity_records_pair_key", table_name="meta_similarity_records"
        )

    columns = {col["name"] for col in inspector.get_columns("meta_similarity_records")}
    if "pair_key" in columns:
        with op.batch_alter_table("meta_similarity_records") as batch_op:
            batch_op.drop_column("pair_key")
