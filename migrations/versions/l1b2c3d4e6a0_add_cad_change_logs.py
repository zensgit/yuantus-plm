"""add cad change logs

Revision ID: l1b2c3d4e6a0
Revises: k1b2c3d4e5f9
Create Date: 2026-01-09 18:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "l1b2c3d4e6a0"
down_revision: Union[str, None] = "k1b2c3d4e5f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "cad_change_logs" in inspector.get_table_names():
        return

    op.create_table(
        "cad_change_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("file_id", sa.String(), nullable=False, index=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("org_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("user_id", sa.Integer(), nullable=True, index=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "cad_change_logs" not in inspector.get_table_names():
        return

    op.drop_table("cad_change_logs")
