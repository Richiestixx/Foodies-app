"""Add submitted_meal and food_items columns to User model

Revision ID: a2ef6de918dd
Revises: d92a86fda215
Create Date: 2023-03-20 15:31:34.327409

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = 'a2ef6de918dd'
down_revision = 'd92a86fda215'
branch_labels = None
depends_on = None

def upgrade():
    conn = op.get_bind()
    conn.execute()

    op.create_table(
        "new_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), index=True, unique=True, nullable=False),
        sa.Column("email", sa.String(120), index=True, unique=True, nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column("submitted_meal", sa.String(100), nullable=True),
        sa.Column("food_items", sa.String(255), nullable=True),
    )

    conn.execute("INSERT INTO new_user (id, username, email, password_hash) SELECT id, username, email, password_hash FROM user")

    op.drop_table("user")
    op.rename_table("new_user", "user")

    conn.execute()


def downgrade():
    conn = op.get_bind()
    conn.execute()

    op.create_table(
        "old_user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), index=True, unique=True, nullable=False),
        sa.Column("email", sa.String(120), index=True, unique=True, nullable=False),
        sa.Column("password_hash", sa.String(128), nullable=False),
    )

    conn.execute("INSERT INTO old_user (id, username, email, password_hash) SELECT id, username, email, password_hash FROM user")

    op.drop_table("user")
    op.rename_table("old_user", "user")

    conn.execute()
