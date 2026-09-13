"""add ai model preferences

Revision ID: e7b50e9463a2
Revises: c7b0e15a4d68
"""

import sqlalchemy as sa
from alembic import op

revision = "e7b50e9463a2"
down_revision = "c7b0e15a4d68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_model_preferences",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["chat_models.id"],
            name=op.f("fk_ai_model_preferences_model_id_chat_models"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_ai_model_preferences_user_id_users")
        ),
        sa.PrimaryKeyConstraint("user_id", "purpose", name=op.f("pk_ai_model_preferences")),
    )


def downgrade() -> None:
    op.drop_table("ai_model_preferences")
