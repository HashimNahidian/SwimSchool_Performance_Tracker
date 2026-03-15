"""new swim school schema

Revision ID: 0001
Revises: a6f0e5f0c1b2
Create Date: 2026-03-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = "a6f0e5f0c1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    return inspect(op.get_bind()).has_table(table_name)


def _column_names(table_name: str) -> set[str]:
    inspector = inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _create_user_role_enum() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role') THEN
                CREATE TYPE user_role AS ENUM ('MANAGER', 'SUPERVISOR', 'INSTRUCTOR');
            END IF;
        END
        $$;
        """
    )


def _create_runtime_objects() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
          NEW.updated_at = NOW();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_evaluations_updated_at ON evaluations;
        CREATE TRIGGER trg_evaluations_updated_at
        BEFORE UPDATE ON evaluations
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_check_skill_attribute ON evaluation_ratings;
        CREATE TRIGGER trg_check_skill_attribute
        BEFORE INSERT OR UPDATE ON evaluation_ratings
        FOR EACH ROW EXECUTE FUNCTION check_skill_attribute();
        """
    )
    op.execute(
        """
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
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_recalculate_final_grade ON evaluation_ratings;
        CREATE TRIGGER trg_recalculate_final_grade
        AFTER INSERT OR UPDATE OR DELETE ON evaluation_ratings
        FOR EACH ROW EXECUTE FUNCTION recalculate_final_grade();
        """
    )
    op.execute(
        """
        CREATE OR REPLACE VIEW evaluation_report_view AS
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
        """
    )


def _create_fresh_schema() -> None:
    _create_user_role_enum()

    op.create_table(
        "schools",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_schools_id"), "schools", ["id"], unique=False)

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

    _create_runtime_objects()


def _upgrade_legacy_schema() -> None:
    _create_user_role_enum()

    user_columns = _column_names("users")
    if "full_name" not in user_columns and "name" in user_columns:
        op.alter_column("users", "name", new_column_name="full_name")
    if "is_active" not in user_columns and "active" in user_columns:
        op.alter_column("users", "active", new_column_name="is_active")
    if "phone" not in _column_names("users"):
        op.add_column("users", sa.Column("phone", sa.String(length=25), nullable=True))

    if "created_at" not in _column_names("schools"):
        op.add_column(
            "schools",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )

    if "created_at" not in _column_names("levels"):
        op.add_column(
            "levels",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
    if "sort_order" not in _column_names("levels"):
        op.add_column("levels", sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False))
        op.execute("UPDATE levels SET sort_order = id WHERE sort_order = 0")

    if "created_at" not in _column_names("skills"):
        op.add_column(
            "skills",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
    if "sort_order" not in _column_names("skills"):
        op.add_column("skills", sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False))
        op.execute("UPDATE skills SET sort_order = id WHERE sort_order = 0")

    if "school_id" not in _column_names("attributes"):
        op.add_column("attributes", sa.Column("school_id", sa.Integer(), nullable=True))
        op.execute(
            """
            UPDATE attributes
            SET school_id = COALESCE(
                (
                    SELECT MIN(sk.school_id)
                    FROM template_attributes ta
                    JOIN templates t ON t.id = ta.template_id
                    JOIN skills sk ON sk.id = t.skill_id
                    WHERE ta.attribute_id = attributes.id
                ),
                (
                    SELECT MIN(e.school_id)
                    FROM evaluation_ratings er
                    JOIN evaluations e ON e.id = er.evaluation_id
                    WHERE er.attribute_id = attributes.id
                ),
                (SELECT MIN(id) FROM schools)
            )
            WHERE school_id IS NULL
            """
        )
        op.alter_column("attributes", "school_id", nullable=False)
    if "created_at" not in _column_names("attributes"):
        op.add_column(
            "attributes",
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
    if "sort_order" not in _column_names("attributes"):
        op.add_column("attributes", sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False))
        op.execute(
            """
            UPDATE attributes
            SET sort_order = COALESCE(
                (SELECT MIN(ta.sort_order) FROM template_attributes ta WHERE ta.attribute_id = attributes.id),
                id
            )
            WHERE sort_order = 0
            """
        )

    if not _table_exists("skill_attributes"):
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

    op.execute(
        """
        INSERT INTO skill_attributes (skill_id, attribute_id)
        SELECT DISTINCT t.skill_id, ta.attribute_id
        FROM template_attributes ta
        JOIN templates t ON t.id = ta.template_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM skill_attributes sa
            WHERE sa.skill_id = t.skill_id
              AND sa.attribute_id = ta.attribute_id
        )
        """
    )
    op.execute(
        """
        INSERT INTO skill_attributes (skill_id, attribute_id)
        SELECT DISTINCT e.skill_id, er.attribute_id
        FROM evaluation_ratings er
        JOIN evaluations e ON e.id = er.evaluation_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM skill_attributes sa
            WHERE sa.skill_id = e.skill_id
              AND sa.attribute_id = er.attribute_id
        )
        """
    )

    if "updated_at" not in _column_names("evaluations"):
        op.add_column("evaluations", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        op.execute(
            "UPDATE evaluations SET updated_at = COALESCE(submitted_at, created_at, NOW()) WHERE updated_at IS NULL"
        )
        op.alter_column("evaluations", "updated_at", nullable=False, server_default=sa.text("now()"))
    if "final_grade" not in _column_names("evaluations"):
        op.add_column("evaluations", sa.Column("final_grade", sa.SmallInteger(), nullable=True))

    if "comment" not in _column_names("evaluation_ratings"):
        op.add_column("evaluation_ratings", sa.Column("comment", sa.Text(), nullable=True))
    if "rating" not in _column_names("evaluation_ratings") and "rating_value" in _column_names("evaluation_ratings"):
        op.alter_column("evaluation_ratings", "rating_value", new_column_name="rating")

    op.execute(
        """
        UPDATE evaluations e
        SET final_grade = stats.avg_rating
        FROM (
            SELECT evaluation_id, ROUND(AVG(rating))::SMALLINT AS avg_rating
            FROM evaluation_ratings
            GROUP BY evaluation_id
        ) stats
        WHERE e.id = stats.evaluation_id
        """
    )

    op.execute(
        """
        ALTER TABLE users
        ALTER COLUMN full_name TYPE VARCHAR(255),
        ALTER COLUMN email TYPE VARCHAR(255),
        ALTER COLUMN password_hash TYPE VARCHAR(512)
        """
    )
    op.execute("ALTER TABLE schools ALTER COLUMN name TYPE VARCHAR(255)")
    op.execute("ALTER TABLE levels ALTER COLUMN name TYPE VARCHAR(100)")
    op.execute("ALTER TABLE skills ALTER COLUMN name TYPE VARCHAR(255)")
    op.execute("ALTER TABLE attributes ALTER COLUMN name TYPE VARCHAR(255)")

    op.execute("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true")
    op.execute("ALTER TABLE levels ALTER COLUMN sort_order SET DEFAULT 0")
    op.execute("ALTER TABLE skills ALTER COLUMN sort_order SET DEFAULT 0")
    op.execute("ALTER TABLE attributes ALTER COLUMN sort_order SET DEFAULT 0")

    op.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_school_id ON users (school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_schools_id ON schools (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_levels_id ON levels (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_levels_school_id ON levels (school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skills_id ON skills (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skills_level_id ON skills (level_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attributes_id ON attributes (id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attributes_school_id ON attributes (school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluations_id ON evaluations (id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_school ON evaluations (school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_instructor ON evaluations (instructor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_supervisor ON evaluations (supervisor_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_skill ON evaluations (skill_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ratings_evaluation ON evaluation_ratings (evaluation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_jti ON refresh_tokens (jti)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs (user_id)")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_school_email') THEN
                ALTER TABLE users ADD CONSTRAINT uq_users_school_email UNIQUE (school_id, email);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_levels_school_name') THEN
                ALTER TABLE levels ADD CONSTRAINT uq_levels_school_name UNIQUE (school_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_skills_level_name') THEN
                ALTER TABLE skills ADD CONSTRAINT uq_skills_level_name UNIQUE (level_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_attributes_school_name') THEN
                ALTER TABLE attributes ADD CONSTRAINT uq_attributes_school_name UNIQUE (school_id, name);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_evaluation_attribute') THEN
                ALTER TABLE evaluation_ratings ADD CONSTRAINT uq_evaluation_attribute UNIQUE (evaluation_id, attribute_id);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_rating_range') THEN
                ALTER TABLE evaluation_ratings ADD CONSTRAINT ck_rating_range CHECK (rating BETWEEN 1 AND 5);
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_different_users') THEN
                ALTER TABLE evaluations ADD CONSTRAINT chk_different_users CHECK (instructor_id <> supervisor_id);
            END IF;
        END
        $$;
        """
    )

    _create_runtime_objects()


def upgrade() -> None:
    if _table_exists("users") and "name" in _column_names("users"):
        _upgrade_legacy_schema()
    else:
        _create_fresh_schema()


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for the schema bridge migration.")
