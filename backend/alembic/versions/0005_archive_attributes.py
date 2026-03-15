"""archive attributes

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-14 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if "is_active" not in _column_names("attributes"):
        op.add_column(
            "attributes",
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for archive schema changes.")
