"""Initial schema — create all persistent Core artifact tables.

Revision ID: 001
Revises:
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("root_path", sa.String(length=4096), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("root_path"),
    )

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("assigned_role", sa.String(length=20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_tasks_workspace_id", "workspace_id"),
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("context_pack_id", sa.String(length=72), nullable=False),
        sa.Column("context_pack", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("execution", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_runs_task_id", "task_id"),
        sa.Index("ix_runs_workspace_id", "workspace_id"),
    )

    op.create_table(
        "guard_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("blocking", sa.Boolean(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_guard_runs_workspace_id", "workspace_id", unique=True),
    )

    op.create_table(
        "vault_inventory_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("built_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_vault_snapshots_workspace_id", "workspace_id", unique=True),
    )

    op.create_table(
        "vault_inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("inventory_id", sa.Uuid(), nullable=False),
        sa.Column("path", sa.String(length=4096), nullable=False),
        sa.Column("name", sa.String(length=1024), nullable=False),
        sa.Column("extension", sa.String(length=80), nullable=True),
        sa.Column("language", sa.String(length=80), nullable=True),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["inventory_id"], ["vault_inventory_snapshots.id"]),
        sa.Index("ix_vault_items_inventory_id", "inventory_id"),
    )

    op.create_table(
        "context_packs",
        sa.Column("id", sa.String(length=72), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=10), nullable=False),
        sa.Column("limits", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("files", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.UniqueConstraint("workspace_id", "id", name="uq_context_pack_workspace"),
        sa.Index("ix_context_packs_workspace_id", "workspace_id"),
    )

    op.create_table(
        "change_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("schema_version", sa.String(length=10), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("context_pack_id", sa.String(length=72), nullable=False),
        sa.Column("provider_id", sa.String(length=40), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("rationale", sa.String(length=2000), nullable=False),
        sa.Column("file_changes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_change_proposals_run_id", "run_id", unique=True),
        sa.Index("ix_change_proposals_workspace_id", "workspace_id"),
    )

    op.create_table(
        "proposal_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("context_pack_id", sa.String(length=72), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("sandbox", sa.JSON(), nullable=False),
        sa.Column("guard", sa.JSON(), nullable=True),
        sa.Column("file_results", sa.JSON(), nullable=False),
        sa.Column("safe_diff", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["proposal_id"], ["change_proposals.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_proposal_verifications_proposal_id", "proposal_id"),
        sa.Index("ix_proposal_verifications_workspace_id", "workspace_id"),
    )

    op.create_table(
        "applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("verification_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("context_pack_id", sa.String(length=72), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("target", sa.JSON(), nullable=False),
        sa.Column("guard", sa.JSON(), nullable=True),
        sa.Column("guard_unavailable_reason", sa.Text(), nullable=True),
        sa.Column("file_results", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=False),
        sa.Column("undo", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["proposal_id"], ["change_proposals.id"]),
        sa.ForeignKeyConstraint(["verification_id"], ["proposal_verifications.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.Index("ix_applications_proposal_id", "proposal_id", unique=True),
        sa.Index("ix_applications_workspace_id", "workspace_id"),
    )


def downgrade() -> None:
    op.drop_table("applications")
    op.drop_table("proposal_verifications")
    op.drop_table("change_proposals")
    op.drop_table("context_packs")
    op.drop_table("vault_inventory_items")
    op.drop_table("vault_inventory_snapshots")
    op.drop_table("guard_runs")
    op.drop_table("runs")
    op.drop_table("tasks")
    op.drop_table("workspaces")
