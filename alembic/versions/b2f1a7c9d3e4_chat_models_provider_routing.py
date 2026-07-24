"""chat_models: per-record provider routing + selector curation

Adds provider/routing columns to chat_models so the in-app model selector maps
to a real provider/model instead of relying on a global LLM_PROVIDER env var.

Revision ID: b2f1a7c9d3e4
Revises: 68c5d0f56056
"""

from alembic import op
import sqlalchemy as sa


revision = "b2f1a7c9d3e4"
down_revision = "68c5d0f56056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_models",
        sa.Column("provider", sa.String(), nullable=False, server_default="other"),
    )
    op.add_column(
        "chat_models",
        sa.Column("supports_tools", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "chat_models",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "chat_models",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "chat_models",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Backfill provider for any pre-existing rows from their model id.
    op.execute("UPDATE chat_models SET provider = 'openai' WHERE name LIKE 'gpt-%' OR name LIKE 'o1%' OR name LIKE 'o3%' OR name LIKE 'o4%'")
    op.execute("UPDATE chat_models SET provider = 'anthropic' WHERE name LIKE 'claude%'")
    op.execute("UPDATE chat_models SET provider = 'google' WHERE name LIKE 'gemini%' OR name LIKE 'palm%'")


def downgrade() -> None:
    op.drop_column("chat_models", "is_active")
    op.drop_column("chat_models", "sort_order")
    op.drop_column("chat_models", "is_default")
    op.drop_column("chat_models", "supports_tools")
    op.drop_column("chat_models", "provider")
