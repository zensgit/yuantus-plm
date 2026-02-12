"""make similarity pair_key not null

Revision ID: y1b2c3d4e7a4
Revises: y1b2c3d4e7a3
Create Date: 2026-02-12 22:10:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "y1b2c3d4e7a4"
down_revision: Union[str, None] = "y1b2c3d4e7a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_similarity_records" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_similarity_records")}
    if "pair_key" not in columns:
        # Older schemas might not have the column; nothing to do.
        return

    # Safety net: ensure no NULL/empty values exist before adding NOT NULL.
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

    if bind.dialect.name == "sqlite":
        # SQLite needs a table rebuild; use Alembic batch mode.
        with op.batch_alter_table("meta_similarity_records") as batch_op:
            batch_op.alter_column(
                "pair_key",
                existing_type=sa.String(length=80),
                nullable=False,
            )
    else:
        op.alter_column(
            "meta_similarity_records",
            "pair_key",
            existing_type=sa.String(length=80),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_similarity_records" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_similarity_records")}
    if "pair_key" not in columns:
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("meta_similarity_records") as batch_op:
            batch_op.alter_column(
                "pair_key",
                existing_type=sa.String(length=80),
                nullable=True,
            )
    else:
        op.alter_column(
            "meta_similarity_records",
            "pair_key",
            existing_type=sa.String(length=80),
            nullable=True,
        )

