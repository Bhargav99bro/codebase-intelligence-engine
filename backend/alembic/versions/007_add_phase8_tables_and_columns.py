"""Add code_duplicates, git_churn_metrics, base_analysis_id, and duplication health score columns

Revision ID: 007_phase8_tables_and_columns
Revises: 006_quality_gate_and_cancel
Create Date: 2026-09-09 21:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "007_phase8_tables_and_columns"
down_revision: Union[str, None] = "006_quality_gate_and_cancel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create code_duplicates table
    op.create_table(
        "code_duplicates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("source_file_id", sa.Uuid(), nullable=True),
        sa.Column("target_file_id", sa.Uuid(), nullable=True),
        sa.Column("source_file_path", sa.String(length=1024), nullable=False),
        sa.Column("target_file_path", sa.String(length=1024), nullable=False),
        sa.Column("clone_type", sa.String(length=16), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("source_start_line", sa.Integer(), nullable=False),
        sa.Column("source_end_line", sa.Integer(), nullable=False),
        sa.Column("target_start_line", sa.Integer(), nullable=False),
        sa.Column("target_end_line", sa.Integer(), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("fragment_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_duplicates_analysis_id", "code_duplicates", ["analysis_id"], unique=False)
    op.create_index("ix_code_duplicates_source_file_id", "code_duplicates", ["source_file_id"], unique=False)
    op.create_index("ix_code_duplicates_target_file_id", "code_duplicates", ["target_file_id"], unique=False)
    op.create_index("ix_code_duplicates_analysis_lines", "code_duplicates", ["analysis_id", "line_count"], unique=False)
    op.create_index("ix_code_duplicates_analysis_paths", "code_duplicates", ["analysis_id", "source_file_path", "target_file_path"], unique=False)

    # 2. Create git_churn_metrics table
    op.create_table(
        "git_churn_metrics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("insertions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("author_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("churn_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("last_modified_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["analysis_id"], ["analysis_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["file_id"], ["repository_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_git_churn_metrics_analysis_id", "git_churn_metrics", ["analysis_id"], unique=False)
    op.create_index("ix_git_churn_metrics_file_id", "git_churn_metrics", ["file_id"], unique=False)
    op.create_index("ix_git_churn_metrics_analysis_path", "git_churn_metrics", ["analysis_id", "file_path"], unique=False)
    op.create_index("ix_git_churn_metrics_analysis_churn", "git_churn_metrics", ["analysis_id", "churn_score"], unique=False)

    # 3. Add duplication columns to analysis_health_scores
    op.add_column("analysis_health_scores", sa.Column("duplication_score", sa.Float(), nullable=False, server_default=sa.text("100.0")))
    op.add_column("analysis_health_scores", sa.Column("duplication_ratio", sa.Float(), nullable=False, server_default=sa.text("0.0")))
    op.add_column("analysis_health_scores", sa.Column("duplicate_blocks_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("analysis_health_scores", sa.Column("duplicate_lines_count", sa.Integer(), nullable=False, server_default=sa.text("0")))

    # 4. Add base_analysis_id and commit_date to analysis_jobs
    op.add_column("analysis_jobs", sa.Column("base_analysis_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_analysis_jobs_base_analysis_id", "analysis_jobs", "analysis_jobs", ["base_analysis_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_analysis_jobs_base_analysis_id", "analysis_jobs", ["base_analysis_id"], unique=False)
    op.add_column("analysis_jobs", sa.Column("commit_date", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_analysis_jobs_commit_date", "analysis_jobs", ["commit_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_commit_date", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "commit_date")
    op.drop_index("ix_analysis_jobs_base_analysis_id", table_name="analysis_jobs")
    op.drop_constraint("fk_analysis_jobs_base_analysis_id", "analysis_jobs", type_="foreignkey")
    op.drop_column("analysis_jobs", "base_analysis_id")

    op.drop_column("analysis_health_scores", "duplicate_lines_count")
    op.drop_column("analysis_health_scores", "duplicate_blocks_count")
    op.drop_column("analysis_health_scores", "duplication_ratio")
    op.drop_column("analysis_health_scores", "duplication_score")

    op.drop_index("ix_git_churn_metrics_analysis_churn", table_name="git_churn_metrics")
    op.drop_index("ix_git_churn_metrics_analysis_path", table_name="git_churn_metrics")
    op.drop_index("ix_git_churn_metrics_file_id", table_name="git_churn_metrics")
    op.drop_index("ix_git_churn_metrics_analysis_id", table_name="git_churn_metrics")
    op.drop_table("git_churn_metrics")

    op.drop_index("ix_code_duplicates_analysis_paths", table_name="code_duplicates")
    op.drop_index("ix_code_duplicates_analysis_lines", table_name="code_duplicates")
    op.drop_index("ix_code_duplicates_target_file_id", table_name="code_duplicates")
    op.drop_index("ix_code_duplicates_source_file_id", table_name="code_duplicates")
    op.drop_index("ix_code_duplicates_analysis_id", table_name="code_duplicates")
    op.drop_table("code_duplicates")
