"""chat_models: per-model Vertex region override

Adds a nullable `region` column so a model can pin to a specific Vertex location
(e.g. Claude -> us-east5) while others use the global default. NULL = use
VERTEX_LOCATION.

Revision ID: c3d2e8f4a1b7
Revises: b2f1a7c9d3e4
"""

from alembic import op
import sqlalchemy as sa


revision = "c3d2e8f4a1b7"
down_revision = "b2f1a7c9d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_models", sa.Column("region", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_models", "region")
