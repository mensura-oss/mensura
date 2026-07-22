"""add Vault index, memory item, and chunk tables

Revision ID: 006_vault_index
Revises: 005_add_job_retry_fields
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vault_index_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("memory_item_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vault_index_snapshots_workspace_id"),
        "vault_index_snapshots",
        ["workspace_id"],
        unique=True,
    )

    op.create_table(
        "vault_memory_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("index_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("source_type", sa.String(length=10), nullable=False),
        sa.Column("language", sa.String(length=80), nullable=True),
        sa.Column("digest", sa.String(length=71), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["index_id"], ["vault_index_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vault_memory_items_index_id"), "vault_memory_items", ["index_id"], unique=False
    )
    op.create_index(
        op.f("ix_vault_memory_items_workspace_id"),
        "vault_memory_items",
        ["workspace_id"],
        unique=False,
    )

    op.create_table(
        "vault_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("memory_item_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column("digest", sa.String(length=71), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("source_type", sa.String(length=10), nullable=False),
        sa.Column("language", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["memory_item_id"], ["vault_memory_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_vault_chunks_memory_item_id"), "vault_chunks", ["memory_item_id"], unique=False
    )
    op.create_index(
        op.f("ix_vault_chunks_workspace_id"), "vault_chunks", ["workspace_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_vault_chunks_workspace_id"), table_name="vault_chunks")
    op.drop_index(op.f("ix_vault_chunks_memory_item_id"), table_name="vault_chunks")
    op.drop_table("vault_chunks")
    op.drop_index(op.f("ix_vault_memory_items_workspace_id"), table_name="vault_memory_items")
    op.drop_index(op.f("ix_vault_memory_items_index_id"), table_name="vault_memory_items")
    op.drop_table("vault_memory_items")
    op.drop_index(op.f("ix_vault_index_snapshots_workspace_id"), table_name="vault_index_snapshots")
    op.drop_table("vault_index_snapshots")
