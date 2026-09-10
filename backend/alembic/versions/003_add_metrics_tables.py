"""Add file_metrics, symbol_metrics tables and summary_metrics column

Revision ID: 003_add_metrics
Revises: 002_add_symbols
Create Date: 2026-09-04 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_add_metrics"
down_revision: Union[str, None] = "002_add_symbols"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add summary_metrics column to analysis_jobs
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "summary_metrics",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # 2. Create file_metrics table
    op.create_table(
        "file_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sloc", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blank_lines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("statement_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("symbol_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("function_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("class_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("method_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("import_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("export_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_nesting_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_nesting_depth", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_cyclomatic_complexity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_cyclomatic_complexity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_cyclomatic_complexity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("maintainability_score", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("metric_status", sa.String(length=50), nullable=False, server_default="calculated"),
        sa.Column("metric_error", sa.Text(), nullable=True),
        sa.Column(
            "quality_flags",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_file_metrics_analysis_id", "file_metrics", ["analysis_id"])
    op.create_index("ix_file_metrics_file_id", "file_metrics", ["file_id"])
    op.create_index("ix_file_metrics_total_cc", "file_metrics", ["total_cyclomatic_complexity"])
    op.create_index("ix_file_metrics_maintainability", "file_metrics", ["maintainability_score"])
    op.create_index("ix_file_metrics_status", "file_metrics", ["metric_status"])

    # 3. Create symbol_metrics table
    op.create_table(
        "symbol_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lines_of_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cyclomatic_complexity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("nesting_depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("parameter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("return_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("branch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("loop_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exception_handler_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("boolean_condition_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "quality_flags",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("metric_status", sa.String(length=50), nullable=False, server_default="calculated"),
        sa.Column("metric_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_symbol_metrics_symbol_id", "symbol_metrics", ["symbol_id"])
    op.create_index("ix_symbol_metrics_analysis_id", "symbol_metrics", ["analysis_id"])
    op.create_index("ix_symbol_metrics_file_id", "symbol_metrics", ["file_id"])
    op.create_index("ix_symbol_metrics_cc", "symbol_metrics", ["cyclomatic_complexity"])


def downgrade() -> None:
    op.drop_table("symbol_metrics")
    op.drop_table("file_metrics")
    op.drop_column("analysis_jobs", "summary_metrics")
