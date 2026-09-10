"""Add dependencies and file_dependency_metrics tables and dependency_summary column

Revision ID: 004_add_dependencies
Revises: 003_add_metrics
Create Date: 2026-09-08 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004_add_dependencies"
down_revision: Union[str, None] = "003_add_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add dependency_summary column to analysis_jobs
    op.add_column(
        "analysis_jobs",
        sa.Column(
            "dependency_summary",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # 2. Create dependencies table
    op.create_table(
        "dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("repository_files.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("target_module", sa.String(length=512), nullable=False),
        sa.Column("dependency_type", sa.String(length=50), nullable=False),
        sa.Column(
            "imported_symbols",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("resolution_status", sa.String(length=50), nullable=False),
        sa.Column("is_type_only", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes on dependencies
    op.create_index("ix_dependencies_analysis_id", "dependencies", ["analysis_id"])
    op.create_index("ix_dependencies_source_file_id", "dependencies", ["source_file_id"])
    op.create_index("ix_dependencies_target_file_id", "dependencies", ["target_file_id"])
    op.create_index("ix_dependencies_resolution_status", "dependencies", ["resolution_status"])
    op.create_index(
        "ix_dependencies_analysis_status",
        "dependencies",
        ["analysis_id", "resolution_status"],
    )
    op.create_index(
        "ix_dependencies_src_target",
        "dependencies",
        ["source_file_id", "target_file_id"],
    )
    op.create_index(
        "uq_dependencies_edge",
        "dependencies",
        ["analysis_id", "source_file_id", "target_module", "line_number"],
        unique=True,
    )

    # 3. Create file_dependency_metrics table
    op.create_table(
        "file_dependency_metrics",
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
        sa.Column("fan_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fan_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("internal_dependencies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_dependencies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unresolved_dependencies_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("instability", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("in_cycle", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("cycle_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Indexes on file_dependency_metrics
    op.create_index("ix_file_dep_metrics_analysis_id", "file_dependency_metrics", ["analysis_id"])
    op.create_index("ix_file_dep_metrics_file_id", "file_dependency_metrics", ["file_id"])
    op.create_index("ix_file_dep_metrics_fan_in", "file_dependency_metrics", ["fan_in"])
    op.create_index("ix_file_dep_metrics_fan_out", "file_dependency_metrics", ["fan_out"])
    op.create_index("ix_file_dep_metrics_instability", "file_dependency_metrics", ["instability"])
    op.create_index("ix_file_dep_metrics_in_cycle", "file_dependency_metrics", ["in_cycle"])


def downgrade() -> None:
    op.drop_table("file_dependency_metrics")
    op.drop_table("dependencies")
    op.drop_column("analysis_jobs", "dependency_summary")
