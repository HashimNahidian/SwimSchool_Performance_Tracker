"""add instructor acknowledged at

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-20 00:00:06.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("evaluations")}
    if "instructor_acknowledged_at" not in columns:
        op.add_column(
            "evaluations",
            sa.Column("instructor_acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for instructor acknowledgment changes.")
