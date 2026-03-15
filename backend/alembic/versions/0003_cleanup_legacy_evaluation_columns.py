"""cleanup legacy evaluation columns

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-14 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect


revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    evaluation_columns = _column_names("evaluations")
    for column in ["level_id", "template_id", "session_label", "session_date", "status", "submitted_at"]:
        if column in evaluation_columns:
            op.drop_column("evaluations", column)

    for table_name in ["schools", "levels", "skills", "attributes"]:
        columns = _column_names(table_name)
        if "active" in columns:
            op.drop_column(table_name, "active")

    skill_columns = _column_names("skills")
    if "school_id" in skill_columns:
        op.drop_column("skills", "school_id")
    if "description" in skill_columns:
        op.drop_column("skills", "description")

    inspector = inspect(op.get_bind())
    if inspector.has_table("template_attributes"):
        op.drop_table("template_attributes")
    if inspector.has_table("templates"):
        op.drop_table("templates")


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for legacy cleanup migration.")
