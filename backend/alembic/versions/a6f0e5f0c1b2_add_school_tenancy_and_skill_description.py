"""add school tenancy and skill description

Revision ID: a6f0e5f0c1b2
Revises: 5e4c8a2d9f10
Create Date: 2026-02-21 12:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a6f0e5f0c1b2"
down_revision: Union[str, Sequence[str], None] = "5e4c8a2d9f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_schools_id"), "schools", ["id"], unique=False)

    op.execute(
        "INSERT INTO schools (name, active) "
        "SELECT 'Default School', true "
        "WHERE NOT EXISTS (SELECT 1 FROM schools WHERE name = 'Default School')"
    )

    op.add_column("users", sa.Column("school_id", sa.Integer(), nullable=True))
    op.add_column("levels", sa.Column("school_id", sa.Integer(), nullable=True))
    op.add_column("skills", sa.Column("school_id", sa.Integer(), nullable=True))
    op.add_column("skills", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("templates", sa.Column("school_id", sa.Integer(), nullable=True))
    op.add_column("evaluations", sa.Column("school_id", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE users SET school_id = (SELECT id FROM schools WHERE name = 'Default School' LIMIT 1) "
        "WHERE school_id IS NULL"
    )
    op.execute(
        "UPDATE levels SET school_id = (SELECT id FROM schools WHERE name = 'Default School' LIMIT 1) "
        "WHERE school_id IS NULL"
    )
    op.execute(
        "UPDATE skills SET school_id = (SELECT id FROM schools WHERE name = 'Default School' LIMIT 1) "
        "WHERE school_id IS NULL"
    )
    op.execute(
        "UPDATE templates SET school_id = (SELECT id FROM schools WHERE name = 'Default School' LIMIT 1) "
        "WHERE school_id IS NULL"
    )
    op.execute(
        "UPDATE evaluations SET school_id = (SELECT id FROM schools WHERE name = 'Default School' LIMIT 1) "
        "WHERE school_id IS NULL"
    )

    op.create_index(op.f("ix_users_school_id"), "users", ["school_id"], unique=False)
    op.create_index(op.f("ix_levels_school_id"), "levels", ["school_id"], unique=False)
    op.create_index(op.f("ix_skills_school_id"), "skills", ["school_id"], unique=False)
    op.create_index(op.f("ix_templates_school_id"), "templates", ["school_id"], unique=False)
    op.create_index(op.f("ix_evaluations_school_id"), "evaluations", ["school_id"], unique=False)

    op.create_foreign_key(
        "fk_users_school_id_schools", "users", "schools", ["school_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_levels_school_id_schools", "levels", "schools", ["school_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_skills_school_id_schools", "skills", "schools", ["school_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_templates_school_id_schools", "templates", "schools", ["school_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_foreign_key(
        "fk_evaluations_school_id_schools", "evaluations", "schools", ["school_id"], ["id"], ondelete="RESTRICT"
    )

    op.alter_column("users", "school_id", nullable=False)
    op.alter_column("levels", "school_id", nullable=False)
    op.alter_column("skills", "school_id", nullable=False)
    op.alter_column("templates", "school_id", nullable=False)
    op.alter_column("evaluations", "school_id", nullable=False)

    op.execute("ALTER TABLE levels DROP CONSTRAINT IF EXISTS levels_name_key")
    op.create_unique_constraint("uq_levels_school_name", "levels", ["school_id", "name"])
    op.create_unique_constraint(
        "uq_templates_name_scope", "templates", ["school_id", "name", "level_id", "skill_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_templates_name_scope", "templates", type_="unique")
    op.drop_constraint("uq_levels_school_name", "levels", type_="unique")

    op.drop_constraint("fk_evaluations_school_id_schools", "evaluations", type_="foreignkey")
    op.drop_constraint("fk_templates_school_id_schools", "templates", type_="foreignkey")
    op.drop_constraint("fk_skills_school_id_schools", "skills", type_="foreignkey")
    op.drop_constraint("fk_levels_school_id_schools", "levels", type_="foreignkey")
    op.drop_constraint("fk_users_school_id_schools", "users", type_="foreignkey")

    op.drop_index(op.f("ix_evaluations_school_id"), table_name="evaluations")
    op.drop_index(op.f("ix_templates_school_id"), table_name="templates")
    op.drop_index(op.f("ix_skills_school_id"), table_name="skills")
    op.drop_index(op.f("ix_levels_school_id"), table_name="levels")
    op.drop_index(op.f("ix_users_school_id"), table_name="users")

    op.drop_column("evaluations", "school_id")
    op.drop_column("templates", "school_id")
    op.drop_column("skills", "description")
    op.drop_column("skills", "school_id")
    op.drop_column("levels", "school_id")
    op.drop_column("users", "school_id")

    op.drop_index(op.f("ix_schools_id"), table_name="schools")
    op.drop_table("schools")
