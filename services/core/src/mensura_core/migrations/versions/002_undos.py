"""add undos table

Revision ID: 002_undos
Revises: 001_initial_schema
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "undos",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "application_id",
            sa.Uuid(),
            sa.ForeignKey("applications.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("file_outcomes", sa.JSON(), nullable=False),
        sa.Column("guard", sa.JSON(), nullable=True),
        sa.Column("guard_unavailable_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_undos_application_id"),
        "undos",
        ["application_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_undos_workspace_id"),
        "undos",
        ["workspace_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_undos_workspace_id"), table_name="undos")
    op.drop_index(op.f("ix_undos_application_id"), table_name="undos")
    op.drop_table("undos")
