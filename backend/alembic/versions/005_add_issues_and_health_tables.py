"""Add analysis_issues and analysis_health_scores tables and health_summary column

Revision ID: 005_add_issues_and_health
Revises: 004_add_dependencies
Create Date: 2026-09-08 13:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "005_add_issues_and_health"
down_revision: Union[str, None] = "004_add_dependencies"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add health_summary column to analysis_jobs
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "health_summary",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # 2. Create analysis_issues table
    op.create_table(
        "analysis_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("rule_id", sa.String(length=32), nullable=False, index=True),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False, index=True),
        sa.Column("severity", sa.String(length=16), nullable=False, index=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("end_line_number", sa.Integer(), nullable=True),
        sa.Column("symbol_name", sa.String(length=255), nullable=True),
        sa.Column("remediation_effort_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "metadata_json",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_analysis_issues_lookup",
        "analysis_issues",
        ["analysis_id", "severity", "category"],
    )
    op.create_index(
        "ix_analysis_issues_file",
        "analysis_issues",
        ["analysis_id", "file_id"],
    )

    # 3. Create analysis_health_scores table
    op.create_table(
        "analysis_health_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("grade", sa.String(length=4), nullable=False),
        sa.Column("maintainability_score", sa.Float(), nullable=False),
        sa.Column("complexity_score", sa.Float(), nullable=False),
        sa.Column("architecture_score", sa.Float(), nullable=False),
        sa.Column("hygiene_score", sa.Float(), nullable=False),
        sa.Column("technical_debt_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("debt_ratio_hours_per_ksloc", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocker_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("major_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("minor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("info_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "category_scores_json",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "recommendations_json",
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


def downgrade() -> None:
    op.drop_table("analysis_health_scores")
    op.drop_index("ix_analysis_issues_file", table_name="analysis_issues")
    op.drop_index("ix_analysis_issues_lookup", table_name="analysis_issues")
    op.drop_table("analysis_issues")
    op.drop_column("analysis_jobs", "health_summary")
