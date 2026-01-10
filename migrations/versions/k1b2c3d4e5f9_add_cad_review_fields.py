"""add cad review fields

Revision ID: k1b2c3d4e5f9
Revises: j1b2c3d4e5f8
Create Date: 2026-01-09 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k1b2c3d4e5f9"
down_revision: Union[str, None] = "j1b2c3d4e5f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_review_state" not in columns:
        op.add_column("meta_files", sa.Column("cad_review_state", sa.String(), nullable=True))
    if "cad_review_note" not in columns:
        op.add_column("meta_files", sa.Column("cad_review_note", sa.Text(), nullable=True))
    if "cad_review_by_id" not in columns:
        op.add_column("meta_files", sa.Column("cad_review_by_id", sa.Integer(), nullable=True))
    if "cad_reviewed_at" not in columns:
        op.add_column("meta_files", sa.Column("cad_reviewed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_files")}
    if "cad_reviewed_at" in columns:
        op.drop_column("meta_files", "cad_reviewed_at")
    if "cad_review_by_id" in columns:
        op.drop_column("meta_files", "cad_review_by_id")
    if "cad_review_note" in columns:
        op.drop_column("meta_files", "cad_review_note")
    if "cad_review_state" in columns:
        op.drop_column("meta_files", "cad_review_state")
