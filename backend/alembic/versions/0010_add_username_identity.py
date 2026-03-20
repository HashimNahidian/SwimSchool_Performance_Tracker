"""add username identity to users

Revision ID: 0010
Revises: 0009
Create Date: 2026-03-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)

    op.execute(
        """
        UPDATE users
        SET username = LOWER(
            COALESCE(
                NULLIF(REGEXP_REPLACE(SPLIT_PART(COALESCE(email, ''), '@', 1), '[^a-zA-Z0-9_]+', '_', 'g'), ''),
                NULLIF(REGEXP_REPLACE(full_name, '[^a-zA-Z0-9_]+', '_', 'g'), ''),
                'user'
            )
        )
        WHERE username IS NULL OR BTRIM(username) = ''
        """
    )

    op.execute(
        """
        UPDATE users
        SET username = CONCAT('user_', id)
        WHERE username IS NULL OR BTRIM(username) = ''
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                username,
                ROW_NUMBER() OVER (PARTITION BY school_id, username ORDER BY id) AS rn
            FROM users
        )
        UPDATE users AS u
        SET username = CONCAT(r.username, '_', u.id)
        FROM ranked AS r
        WHERE u.id = r.id AND r.rn > 1
        """
    )

    op.alter_column("users", "username", existing_type=sa.String(length=50), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=True)
    op.create_unique_constraint("uq_users_school_username", "users", ["school_id", "username"])


def downgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET email = CONCAT(username, '@legacy.local')
        WHERE email IS NULL OR BTRIM(email) = ''
        """
    )
    op.drop_constraint("uq_users_school_username", "users", type_="unique")
    op.alter_column("users", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "username")
