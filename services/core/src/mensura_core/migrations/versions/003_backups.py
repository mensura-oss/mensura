"""add backups table

Revision ID: 003_backups
Revises: 002_undos
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("db_version", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256_hex", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False, unique=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backups_created_at"),
        "backups",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_backups_storage_path"),
        "backups",
        ["storage_path"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_backups_storage_path"), table_name="backups")
    op.drop_index(op.f("ix_backups_created_at"), table_name="backups")
    op.drop_table("backups")
