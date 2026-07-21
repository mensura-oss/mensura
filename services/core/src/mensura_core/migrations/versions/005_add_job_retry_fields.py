"""add retry linkage fields to jobs table

Revision ID: 005_add_job_retry_fields
Revises: 004_jobs
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("retry_of_job_id", sa.Uuid(), nullable=True))
    op.add_column("jobs", sa.Column("root_job_id", sa.Uuid(), nullable=True))
    op.add_column(
        "jobs",
        sa.Column("retry_eligible", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column(
        "jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("jobs", "retry_count")
    op.drop_column("jobs", "retry_eligible")
    op.drop_column("jobs", "root_job_id")
    op.drop_column("jobs", "retry_of_job_id")
