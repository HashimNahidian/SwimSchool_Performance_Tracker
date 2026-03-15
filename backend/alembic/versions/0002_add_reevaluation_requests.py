"""add reevaluation requests

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reevaluation_status') THEN
                CREATE TYPE reevaluation_status AS ENUM ('OPEN', 'COMPLETED', 'CANCELED');
            END IF;
        END
        $$;
        """
    )

    if "needs_reevaluation" not in _column_names("evaluations"):
        op.add_column(
            "evaluations",
            sa.Column("needs_reevaluation", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if not _table_exists("reevaluation_requests"):
        op.create_table(
            "reevaluation_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("school_id", sa.Integer(), nullable=False),
            sa.Column("instructor_id", sa.Integer(), nullable=False),
            sa.Column("supervisor_id", sa.Integer(), nullable=True),
            sa.Column("skill_id", sa.Integer(), nullable=False),
            sa.Column("source_evaluation_id", sa.Integer(), nullable=True),
            sa.Column(
                "status",
                postgresql.ENUM(
                    "OPEN",
                    "COMPLETED",
                    "CANCELED",
                    name="reevaluation_status",
                    create_type=False,
                ),
                nullable=False,
                server_default="OPEN",
            ),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(["instructor_id"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["source_evaluation_id"], ["evaluations.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_reevaluation_requests_id"), "reevaluation_requests", ["id"], unique=False)
        op.create_index(op.f("ix_reevaluation_requests_school_id"), "reevaluation_requests", ["school_id"], unique=False)
        op.create_index(op.f("ix_reevaluation_requests_instructor_id"), "reevaluation_requests", ["instructor_id"], unique=False)
        op.create_index(op.f("ix_reevaluation_requests_supervisor_id"), "reevaluation_requests", ["supervisor_id"], unique=False)
        op.create_index(op.f("ix_reevaluation_requests_skill_id"), "reevaluation_requests", ["skill_id"], unique=False)
        op.create_index(
            op.f("ix_reevaluation_requests_source_evaluation_id"),
            "reevaluation_requests",
            ["source_evaluation_id"],
            unique=False,
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for reevaluation schema changes.")
