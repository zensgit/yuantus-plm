"""add version file checkout fields

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-04-15 18:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TABLE = "meta_version_files"
_FK = "fk_meta_version_files_checked_out_by_id_rbac_users"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(_TABLE)}

    if "checked_out_by_id" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("checked_out_by_id", sa.Integer(), nullable=True),
        )
    if "checked_out_at" not in columns:
        op.add_column(
            _TABLE,
            sa.Column("checked_out_at", sa.DateTime(), nullable=True),
        )

    foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys(_TABLE)}
    if _FK not in foreign_keys:
        op.create_foreign_key(
            _FK,
            _TABLE,
            "rbac_users",
            ["checked_out_by_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns(_TABLE)}
    foreign_keys = {fk.get("name") for fk in inspector.get_foreign_keys(_TABLE)}

    if _FK in foreign_keys:
        op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    if "checked_out_at" in columns:
        op.drop_column(_TABLE, "checked_out_at")
    if "checked_out_by_id" in columns:
        op.drop_column(_TABLE, "checked_out_by_id")
