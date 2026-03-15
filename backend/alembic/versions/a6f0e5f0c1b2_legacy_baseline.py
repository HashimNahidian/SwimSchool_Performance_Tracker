"""legacy baseline placeholder

Revision ID: a6f0e5f0c1b2
Revises:
Create Date: 2026-02-24 00:00:00.000000

This revision exists only so legacy databases stamped with this version
can be upgraded into the current schema by the next migration.
"""

from typing import Sequence, Union


revision: str = "a6f0e5f0c1b2"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
