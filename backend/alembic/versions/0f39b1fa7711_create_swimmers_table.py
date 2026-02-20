"""create initial propel evaluation schema

Revision ID: 0f39b1fa7711
Revises: 
Create Date: 2026-02-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0f39b1fa7711'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    user_role = sa.Enum("MANAGER", "SUPERVISOR", "INSTRUCTOR", name="user_role")
    evaluation_status = sa.Enum("DRAFT", "SUBMITTED", name="evaluation_status")
    user_role.create(op.get_bind(), checkfirst=True)
    evaluation_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_levels_id"), "levels", ["id"], unique=False)

    op.create_table(
        "attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_attributes_id"), "attributes", ["id"], unique=False)

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level_id", "name", name="uq_skills_level_name"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)
    op.create_index(op.f("ix_skills_level_id"), "skills", ["level_id"], unique=False)

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "level_id", "skill_id", name="uq_templates_name_scope"),
    )
    op.create_index(op.f("ix_templates_id"), "templates", ["id"], unique=False)
    op.create_index(op.f("ix_templates_level_id"), "templates", ["level_id"], unique=False)
    op.create_index(op.f("ix_templates_skill_id"), "templates", ["skill_id"], unique=False)

    op.create_table(
        "template_attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_id"], ["attributes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "attribute_id", name="uq_template_attribute"),
    )
    op.create_index(op.f("ix_template_attributes_attribute_id"), "template_attributes", ["attribute_id"], unique=False)
    op.create_index(op.f("ix_template_attributes_id"), "template_attributes", ["id"], unique=False)
    op.create_index(op.f("ix_template_attributes_template_id"), "template_attributes", ["template_id"], unique=False)

    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("supervisor_id", sa.Integer(), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=True),
        sa.Column("skill_id", sa.Integer(), nullable=True),
        sa.Column("session_label", sa.String(length=120), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", evaluation_status, server_default="DRAFT", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["instructor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluations_id"), "evaluations", ["id"], unique=False)
    op.create_index(op.f("ix_evaluations_instructor_id"), "evaluations", ["instructor_id"], unique=False)
    op.create_index(op.f("ix_evaluations_level_id"), "evaluations", ["level_id"], unique=False)
    op.create_index(op.f("ix_evaluations_skill_id"), "evaluations", ["skill_id"], unique=False)
    op.create_index(op.f("ix_evaluations_supervisor_id"), "evaluations", ["supervisor_id"], unique=False)

    op.create_table(
        "evaluation_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.Column("rating_value", sa.Integer(), nullable=False),
        sa.CheckConstraint("rating_value IN (1, 2, 3)", name="ck_rating_value_range"),
        sa.ForeignKeyConstraint(["attribute_id"], ["attributes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "attribute_id", name="uq_eval_rating"),
    )
    op.create_index(op.f("ix_evaluation_ratings_attribute_id"), "evaluation_ratings", ["attribute_id"], unique=False)
    op.create_index(op.f("ix_evaluation_ratings_evaluation_id"), "evaluation_ratings", ["evaluation_id"], unique=False)
    op.create_index(op.f("ix_evaluation_ratings_id"), "evaluation_ratings", ["id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_evaluation_ratings_id"), table_name="evaluation_ratings")
    op.drop_index(op.f("ix_evaluation_ratings_evaluation_id"), table_name="evaluation_ratings")
    op.drop_index(op.f("ix_evaluation_ratings_attribute_id"), table_name="evaluation_ratings")
    op.drop_table("evaluation_ratings")

    op.drop_index(op.f("ix_evaluations_supervisor_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_skill_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_level_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_instructor_id"), table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_id"), table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index(op.f("ix_template_attributes_template_id"), table_name="template_attributes")
    op.drop_index(op.f("ix_template_attributes_id"), table_name="template_attributes")
    op.drop_index(op.f("ix_template_attributes_attribute_id"), table_name="template_attributes")
    op.drop_table("template_attributes")

    op.drop_index(op.f("ix_templates_skill_id"), table_name="templates")
    op.drop_index(op.f("ix_templates_level_id"), table_name="templates")
    op.drop_index(op.f("ix_templates_id"), table_name="templates")
    op.drop_table("templates")

    op.drop_index(op.f("ix_skills_level_id"), table_name="skills")
    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")

    op.drop_index(op.f("ix_attributes_id"), table_name="attributes")
    op.drop_table("attributes")

    op.drop_index(op.f("ix_levels_id"), table_name="levels")
    op.drop_table("levels")

    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    sa.Enum(name="evaluation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
