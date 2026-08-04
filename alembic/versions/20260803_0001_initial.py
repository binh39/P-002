"""Create experiments, candidates, and approvals.

Revision ID: 20260803_0001
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260803_0001"
down_revision = None
branch_labels = None
depends_on = None

prompt_status = sa.Enum(
    "DRAFT",
    "OPTIMIZED",
    "IN_REVIEW",
    "APPROVED",
    "REJECTED",
    "FAILED",
    name="promptstatus",
)


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("baseline_prompt", sa.Text(), nullable=False),
        sa.Column("module_path", sa.String(length=1000), nullable=False),
        sa.Column("dataset_path", sa.String(length=1000), nullable=False),
        sa.Column("source_root", sa.String(length=1000), nullable=False),
        sa.Column("budget_limit", sa.Float(), nullable=False),
        sa.Column("status", prompt_status, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("experiment_id", sa.String(), nullable=False),
        sa.Column("parent_id", sa.String(), nullable=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("fitness_score", sa.Float(), nullable=False),
        sa.Column("pass_rate", sa.Float(), nullable=False),
        sa.Column("statement_coverage", sa.Float(), nullable=False),
        sa.Column("branch_coverage", sa.Float(), nullable=False),
        sa.Column("mutation_score", sa.Float(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
        sa.Column("latency_seconds", sa.Float(), nullable=False),
        sa.Column("status", prompt_status, nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidates_experiment_id"),
        "candidates",
        ["experiment_id"],
    )
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("candidate_id", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.String(length=200), nullable=False),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_approvals_candidate_id"),
        "approvals",
        ["candidate_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_approvals_candidate_id"), table_name="approvals")
    op.drop_table("approvals")
    op.drop_index(op.f("ix_candidates_experiment_id"), table_name="candidates")
    op.drop_table("candidates")
    op.drop_table("experiments")
    prompt_status.drop(op.get_bind(), checkfirst=True)
