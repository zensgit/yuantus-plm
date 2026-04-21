"""add numbering sequences

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-04-20 20:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_numbering_sequences" in inspector.get_table_names():
        return

    op.create_table(
        "meta_numbering_sequences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("item_type_id", sa.String(length=120), nullable=False),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("org_id", sa.String(length=120), nullable=False),
        sa.Column("prefix", sa.String(length=120), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "item_type_id",
            "tenant_id",
            "org_id",
            "prefix",
            name="uq_numbering_sequence_scope",
        ),
    )
    op.create_index(
        "ix_meta_numbering_sequences_item_type_id",
        "meta_numbering_sequences",
        ["item_type_id"],
    )
    op.create_index(
        "ix_meta_numbering_sequences_tenant_id",
        "meta_numbering_sequences",
        ["tenant_id"],
    )
    op.create_index(
        "ix_meta_numbering_sequences_org_id",
        "meta_numbering_sequences",
        ["org_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "meta_numbering_sequences" not in inspector.get_table_names():
        return

    op.drop_index(
        "ix_meta_numbering_sequences_org_id",
        table_name="meta_numbering_sequences",
    )
    op.drop_index(
        "ix_meta_numbering_sequences_tenant_id",
        table_name="meta_numbering_sequences",
    )
    op.drop_index(
        "ix_meta_numbering_sequences_item_type_id",
        table_name="meta_numbering_sequences",
    )
    op.drop_table("meta_numbering_sequences")
