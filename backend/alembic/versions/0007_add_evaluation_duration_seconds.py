"""add evaluation duration seconds

Revision ID: 0007
Revises: 0006
Create Date: 2026-03-19 00:00:04.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("evaluations")}
    if "duration_seconds" not in columns:
        op.add_column("evaluations", sa.Column("duration_seconds", sa.Integer(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for evaluation duration changes.")
