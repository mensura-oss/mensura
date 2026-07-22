"""add Vault chunk postings (sparse inverted index for sub-linear search)

Revision ID: 007_vault_chunk_postings
Revises: 006_vault_index
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vault_chunk_postings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("bucket", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    # The lookup path: a search reads only the posting lists for its own query buckets.
    op.create_index(
        "ix_vault_chunk_postings_workspace_id_bucket",
        "vault_chunk_postings",
        ["workspace_id", "bucket"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_vault_chunk_postings_workspace_id_bucket", table_name="vault_chunk_postings"
    )
    op.drop_table("vault_chunk_postings")
