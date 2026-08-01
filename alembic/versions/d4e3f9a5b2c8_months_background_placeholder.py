"""months: inline blurred preview for the background image

Adds a nullable `background_placeholder` holding a ~32px WebP `data:` URI,
generated in the browser at upload time. NULL for months saved before this
existed; the client falls back to a flat colour.

Revision ID: d4e3f9a5b2c8
Revises: c3d2e8f4a1b7
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e3f9a5b2c8"
down_revision = "c3d2e8f4a1b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("months", sa.Column("background_placeholder", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("months", "background_placeholder")
