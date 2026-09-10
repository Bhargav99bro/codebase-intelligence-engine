"""Add symbols table and parser status fields

Revision ID: 002_add_symbols
Revises: 001_initial_schema
Create Date: 2026-09-04 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_symbols"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add Phase 3 columns to repository_files
    op.add_column(
        "repository_files",
        sa.Column("parser_status", sa.String(length=50), nullable=False, server_default="pending"),
    )
    op.add_column(
        "repository_files",
        sa.Column("parser_error", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "repository_files",
        sa.Column("symbol_count", sa.Integer(), nullable=False, server_default="0"),
    )

    # 2. Add Phase 3 columns to analysis_jobs
    op.add_column(
        "analysis_jobs",
        sa.Column("total_symbols", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("symbol_distribution", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="{}"),
    )

    # 3. Create symbols table
    op.create_table(
        "symbols",
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
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("symbol_type", sa.String(length=50), nullable=False),
        sa.Column("qualified_name", sa.String(length=1024), nullable=True),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("start_column", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("end_column", sa.Integer(), nullable=False),
        sa.Column(
            "parent_symbol_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("symbols.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("signature", sa.String(length=1024), nullable=True),
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
            server_default=sa.func.now(),
        ),
    )

    # 4. Create indexes for symbols
    op.create_index("ix_symbols_analysis_id", "symbols", ["analysis_id"])
    op.create_index("ix_symbols_file_id", "symbols", ["file_id"])
    op.create_index("ix_symbols_name", "symbols", ["name"])
    op.create_index("ix_symbols_symbol_type", "symbols", ["symbol_type"])
    op.create_index("ix_symbols_qualified_name", "symbols", ["qualified_name"])
    op.create_index("ix_symbols_parent_symbol_id", "symbols", ["parent_symbol_id"])


def downgrade() -> None:
    op.drop_index("ix_symbols_parent_symbol_id", table_name="symbols")
    op.drop_index("ix_symbols_qualified_name", table_name="symbols")
    op.drop_index("ix_symbols_symbol_type", table_name="symbols")
    op.drop_index("ix_symbols_name", table_name="symbols")
    op.drop_index("ix_symbols_file_id", table_name="symbols")
    op.drop_index("ix_symbols_analysis_id", table_name="symbols")
    op.drop_table("symbols")

    op.drop_column("analysis_jobs", "symbol_distribution")
    op.drop_column("analysis_jobs", "total_symbols")

    op.drop_column("repository_files", "symbol_count")
    op.drop_column("repository_files", "parser_error")
    op.drop_column("repository_files", "parser_status")
