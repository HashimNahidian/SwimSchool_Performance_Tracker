"""add scheduled evaluations

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-20 00:00:05.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    enums = {item["name"] for item in inspector.get_enums()}
    if "scheduled_evaluation_status" not in enums:
        scheduled_status = sa.Enum(
            "PENDING",
            "IN_PROGRESS",
            "COMPLETED",
            "CANCELED",
            name="scheduled_evaluation_status",
        )
        scheduled_status.create(bind, checkfirst=True)
    scheduled_status_type = postgresql.ENUM(
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "CANCELED",
        name="scheduled_evaluation_status",
        create_type=False,
    )

    if not inspector.has_table("scheduled_evaluations"):
        op.create_table(
            "scheduled_evaluations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("school_id", sa.Integer(), sa.ForeignKey("schools.id", ondelete="CASCADE"), nullable=False),
            sa.Column("instructor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("target_date", sa.Date(), nullable=False),
            sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("assigned_to_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column(
                "status",
                scheduled_status_type,
                nullable=False,
                server_default="PENDING",
            ),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_scheduled_evaluations_school_id", "scheduled_evaluations", ["school_id"])
        op.create_index("ix_scheduled_evaluations_instructor_id", "scheduled_evaluations", ["instructor_id"])
        op.create_index("ix_scheduled_evaluations_skill_id", "scheduled_evaluations", ["skill_id"])
        op.create_index("ix_scheduled_evaluations_requested_by_id", "scheduled_evaluations", ["requested_by_id"])
        op.create_index("ix_scheduled_evaluations_assigned_to_id", "scheduled_evaluations", ["assigned_to_id"])

    evaluation_columns = {column["name"] for column in inspector.get_columns("evaluations")}
    if "scheduled_evaluation_id" not in evaluation_columns:
        op.add_column(
            "evaluations",
            sa.Column(
                "scheduled_evaluation_id",
                sa.Integer(),
                sa.ForeignKey("scheduled_evaluations.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_evaluations_scheduled_evaluation_id", "evaluations", ["scheduled_evaluation_id"])


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for scheduled evaluation changes.")
