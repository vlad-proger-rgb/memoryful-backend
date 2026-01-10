from alembic import op
import sqlalchemy as sa


revision = 'd8d2b6ad0e4b'
down_revision = 'c3f2c0a1b8f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('days', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('days', sa.Column('ai_generated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('days', 'ai_generated_at')
    op.drop_column('days', 'completed_at')
