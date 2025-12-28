"""add cad connector id and job dedupe key

Revision ID: b7c9d2e1f4a6
Revises: a1b2c3d4e5f6
Create Date: 2025-12-21 13:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7c9d2e1f4a6"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_files" in inspector.get_table_names():
        file_columns = {col["name"] for col in inspector.get_columns("meta_files")}
        if "cad_connector_id" not in file_columns:
            op.add_column("meta_files", sa.Column("cad_connector_id", sa.String(), nullable=True))

    if "meta_conversion_jobs" in inspector.get_table_names():
        job_columns = {col["name"] for col in inspector.get_columns("meta_conversion_jobs")}
        if "dedupe_key" not in job_columns:
            op.add_column("meta_conversion_jobs", sa.Column("dedupe_key", sa.String(length=120), nullable=True))

        existing_indexes = {ix.get("name") for ix in inspector.get_indexes("meta_conversion_jobs")}
        index_name = op.f("ix_meta_conversion_jobs_dedupe_key")
        if index_name not in existing_indexes:
            op.create_index(index_name, "meta_conversion_jobs", ["dedupe_key"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_conversion_jobs" in inspector.get_table_names():
        existing_indexes = {ix.get("name") for ix in inspector.get_indexes("meta_conversion_jobs")}
        index_name = op.f("ix_meta_conversion_jobs_dedupe_key")
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="meta_conversion_jobs")

        job_columns = {col["name"] for col in inspector.get_columns("meta_conversion_jobs")}
        if "dedupe_key" in job_columns:
            op.drop_column("meta_conversion_jobs", "dedupe_key")

    if "meta_files" in inspector.get_table_names():
        file_columns = {col["name"] for col in inspector.get_columns("meta_files")}
        if "cad_connector_id" in file_columns:
            op.drop_column("meta_files", "cad_connector_id")
