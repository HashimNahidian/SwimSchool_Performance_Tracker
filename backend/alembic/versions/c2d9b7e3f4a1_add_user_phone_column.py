"""add user phone column

Revision ID: c2d9b7e3f4a1
Revises: a6f0e5f0c1b2
Create Date: 2026-03-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d9b7e3f4a1"
down_revision: Union[str, Sequence[str], None] = "a6f0e5f0c1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=25), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")

