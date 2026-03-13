"""new swim school schema

Revision ID: 0001
Revises:
Create Date: 2026-03-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── schools ───────────────────────────────────────────────────────────────
    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_schools_id"), "schools", ["id"], unique=False)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=25), nullable=True),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.Enum("MANAGER", "SUPERVISOR", "INSTRUCTOR", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "email", name="uq_users_school_email"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_school_id"), "users", ["school_id"], unique=False)

    # ── levels ────────────────────────────────────────────────────────────────
    op.create_table(
        "levels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "name", name="uq_levels_school_name"),
    )
    op.create_index(op.f("ix_levels_id"), "levels", ["id"], unique=False)
    op.create_index(op.f("ix_levels_school_id"), "levels", ["school_id"], unique=False)

    # ── skills ────────────────────────────────────────────────────────────────
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["level_id"], ["levels.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("level_id", "name", name="uq_skills_level_name"),
    )
    op.create_index(op.f("ix_skills_id"), "skills", ["id"], unique=False)
    op.create_index(op.f("ix_skills_level_id"), "skills", ["level_id"], unique=False)

    # ── attributes ────────────────────────────────────────────────────────────
    op.create_table(
        "attributes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "name", name="uq_attributes_school_name"),
    )
    op.create_index(op.f("ix_attributes_id"), "attributes", ["id"], unique=False)
    op.create_index(op.f("ix_attributes_school_id"), "attributes", ["school_id"], unique=False)

    # ── skill_attributes ──────────────────────────────────────────────────────
    op.create_table(
        "skill_attributes",
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_id"], ["attributes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("skill_id", "attribute_id"),
    )
    op.create_index("idx_skill_attributes_skill", "skill_attributes", ["skill_id"], unique=False)
    op.create_index("idx_skill_attributes_attribute", "skill_attributes", ["attribute_id"], unique=False)

    # ── evaluations ───────────────────────────────────────────────────────────
    op.create_table(
        "evaluations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("school_id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("supervisor_id", sa.Integer(), nullable=False),
        sa.Column("skill_id", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("final_grade", sa.SmallInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("instructor_id <> supervisor_id", name="chk_different_users"),
        sa.ForeignKeyConstraint(["instructor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"]),
        sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluations_id"), "evaluations", ["id"], unique=False)
    op.create_index("idx_evaluations_school", "evaluations", ["school_id"], unique=False)
    op.create_index("idx_evaluations_instructor", "evaluations", ["instructor_id"], unique=False)
    op.create_index("idx_evaluations_supervisor", "evaluations", ["supervisor_id"], unique=False)
    op.create_index("idx_evaluations_skill", "evaluations", ["skill_id"], unique=False)

    # ── evaluation_ratings ────────────────────────────────────────────────────
    op.create_table(
        "evaluation_ratings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("attribute_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
        sa.ForeignKeyConstraint(["attribute_id"], ["attributes.id"]),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evaluation_id", "attribute_id", name="uq_evaluation_attribute"),
    )
    op.create_index("idx_ratings_evaluation", "evaluation_ratings", ["evaluation_id"], unique=False)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(op.f("ix_refresh_tokens_jti"), "refresh_tokens", ["jti"], unique=False)
    op.create_index(op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False)

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("client_ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)

    # ── Triggers ──────────────────────────────────────────────────────────────

    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_evaluations_updated_at
        BEFORE UPDATE ON evaluations
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION check_skill_attribute()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM skill_attributes sa
                JOIN evaluations e ON e.skill_id = sa.skill_id
                WHERE e.id = NEW.evaluation_id
                  AND sa.attribute_id = NEW.attribute_id
            ) THEN
                RAISE EXCEPTION 'Attribute % is not configured for the skill on evaluation %',
                    NEW.attribute_id, NEW.evaluation_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_check_skill_attribute
        BEFORE INSERT OR UPDATE ON evaluation_ratings
        FOR EACH ROW EXECUTE FUNCTION check_skill_attribute();
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION recalculate_final_grade()
        RETURNS TRIGGER AS $$
        DECLARE
            v_evaluation_id INT;
        BEGIN
            IF TG_OP = 'DELETE' THEN
                v_evaluation_id := OLD.evaluation_id;
            ELSE
                v_evaluation_id := NEW.evaluation_id;
            END IF;

            UPDATE evaluations
            SET final_grade = (
                SELECT ROUND(AVG(rating))::SMALLINT
                FROM evaluation_ratings
                WHERE evaluation_id = v_evaluation_id
            )
            WHERE id = v_evaluation_id;

            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trg_recalculate_final_grade
        AFTER INSERT OR UPDATE OR DELETE ON evaluation_ratings
        FOR EACH ROW EXECUTE FUNCTION recalculate_final_grade();
    """)

    # ── View ──────────────────────────────────────────────────────────────────

    op.execute("""
        CREATE VIEW evaluation_report_view AS
        SELECT
            e.id                    AS evaluation_id,
            s.name                  AS school_name,
            lv.name                 AS level_name,
            sk.name                 AS skill_name,
            instructor.full_name    AS instructor_name,
            instructor.is_active    AS instructor_active,
            supervisor.full_name    AS supervisor_name,
            supervisor.is_active    AS supervisor_active,
            e.notes,
            e.final_grade,
            e.created_at,
            e.updated_at,
            a.name                  AS attribute_name,
            a.sort_order            AS attribute_order,
            er.rating,
            er.comment              AS rating_comment
        FROM evaluations e
        JOIN schools       s          ON s.id  = e.school_id
        JOIN skills        sk         ON sk.id = e.skill_id
        JOIN levels        lv         ON lv.id = sk.level_id
        JOIN users         instructor ON instructor.id = e.instructor_id
        JOIN users         supervisor ON supervisor.id = e.supervisor_id
        JOIN evaluation_ratings er    ON er.evaluation_id = e.id
        JOIN attributes    a          ON a.id  = er.attribute_id
        ORDER BY e.id, a.sort_order;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS evaluation_report_view")

    op.execute("DROP TRIGGER IF EXISTS trg_recalculate_final_grade ON evaluation_ratings")
    op.execute("DROP FUNCTION IF EXISTS recalculate_final_grade()")

    op.execute("DROP TRIGGER IF EXISTS trg_check_skill_attribute ON evaluation_ratings")
    op.execute("DROP FUNCTION IF EXISTS check_skill_attribute()")

    op.execute("DROP TRIGGER IF EXISTS trg_evaluations_updated_at ON evaluations")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_jti"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("idx_ratings_evaluation", table_name="evaluation_ratings")
    op.drop_table("evaluation_ratings")

    op.drop_index("idx_evaluations_skill", table_name="evaluations")
    op.drop_index("idx_evaluations_supervisor", table_name="evaluations")
    op.drop_index("idx_evaluations_instructor", table_name="evaluations")
    op.drop_index("idx_evaluations_school", table_name="evaluations")
    op.drop_index(op.f("ix_evaluations_id"), table_name="evaluations")
    op.drop_table("evaluations")

    op.drop_index("idx_skill_attributes_attribute", table_name="skill_attributes")
    op.drop_index("idx_skill_attributes_skill", table_name="skill_attributes")
    op.drop_table("skill_attributes")

    op.drop_index(op.f("ix_attributes_school_id"), table_name="attributes")
    op.drop_index(op.f("ix_attributes_id"), table_name="attributes")
    op.drop_table("attributes")

    op.drop_index(op.f("ix_skills_level_id"), table_name="skills")
    op.drop_index(op.f("ix_skills_id"), table_name="skills")
    op.drop_table("skills")

    op.drop_index(op.f("ix_levels_school_id"), table_name="levels")
    op.drop_index(op.f("ix_levels_id"), table_name="levels")
    op.drop_table("levels")

    op.drop_index(op.f("ix_users_school_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_schools_id"), table_name="schools")
    op.drop_table("schools")

    op.execute("DROP TYPE IF EXISTS user_role")
