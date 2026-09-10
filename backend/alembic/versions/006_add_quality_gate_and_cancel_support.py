"""Add quality_gate_status, quality_gate_details, and is_cancelled to analysis_jobs

Revision ID: 006_quality_gate_and_cancel
Revises: 005_add_issues_and_health
Create Date: 2026-09-08 14:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "006_quality_gate_and_cancel"
down_revision: Union[str, None] = "005_add_issues_and_health"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_jobs",
        sa.Column("quality_gate_status", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("quality_gate_details", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index(
        "ix_analysis_jobs_quality_gate_status",
        "analysis_jobs",
        ["quality_gate_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_jobs_quality_gate_status", table_name="analysis_jobs")
    op.drop_column("analysis_jobs", "is_cancelled")
    op.drop_column("analysis_jobs", "quality_gate_details")
    op.drop_column("analysis_jobs", "quality_gate_status")
