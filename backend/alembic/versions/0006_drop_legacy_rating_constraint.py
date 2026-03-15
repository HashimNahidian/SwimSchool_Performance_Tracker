"""drop legacy rating constraint

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-14 00:00:03.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE evaluation_ratings DROP CONSTRAINT IF EXISTS ck_rating_value_range")


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for legacy constraint cleanup.")
