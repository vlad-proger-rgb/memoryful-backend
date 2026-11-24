from alembic import op
import sqlalchemy as sa


revision = '93aa2c474151'
down_revision = '43b38d5fc10d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tokens issued before sessions had a stable id can never refresh again.
    op.execute("DELETE FROM user_tokens")
    op.add_column('user_tokens', sa.Column('previous_refresh_token_hash', sa.String(), nullable=True))
    op.add_column('user_tokens', sa.Column('rotated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('user_tokens', 'rotated_at')
    op.drop_column('user_tokens', 'previous_refresh_token_hash')
