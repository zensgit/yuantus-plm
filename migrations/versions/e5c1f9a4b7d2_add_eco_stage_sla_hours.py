"""add eco stage sla hours

Revision ID: e5c1f9a4b7d2
Revises: f87ce5711ce1
Create Date: 2025-12-19 23:24:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e5c1f9a4b7d2"
down_revision: Union[str, None] = "f87ce5711ce1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_eco_stages" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_eco_stages")}
    if "sla_hours" not in columns:
        op.add_column(
            "meta_eco_stages",
            sa.Column("sla_hours", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_eco_stages" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("meta_eco_stages")}
    if "sla_hours" in columns:
        op.drop_column("meta_eco_stages", "sla_hours")
