"""add week digests

Revision ID: c7b0e15a4d68
Revises: a1f4c7d2e903

One row per user per finished week, keyed by the Monday it starts on.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c7b0e15a4d68"
down_revision = "a1f4c7d2e903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "week_digests",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_day_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"], ["chat_models.id"], name=op.f("fk_week_digests_model_id_chat_models")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_week_digests_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_week_digests")),
        sa.UniqueConstraint("user_id", "week_start", name=op.f("uq_week_digests_user_id")),
    )


def downgrade() -> None:
    op.drop_table("week_digests")
