from alembic import op
import sqlalchemy as sa


revision = 'c3f2c0a1b8f7'
down_revision = '6b1b9d6d44c8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('insights', sa.Column('description', sa.String(), nullable=False, server_default=''))
    op.add_column('insights', sa.Column('icon', sa.JSON(), nullable=True))

    op.add_column('suggestions', sa.Column('description', sa.String(), nullable=False, server_default=''))
    op.add_column('suggestions', sa.Column('icon', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('suggestions', 'icon')
    op.drop_column('suggestions', 'description')

    op.drop_column('insights', 'icon')
    op.drop_column('insights', 'description')
