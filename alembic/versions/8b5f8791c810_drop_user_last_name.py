
import sqlalchemy as sa
from alembic import op

revision = '8b5f8791c810'
down_revision = 'eb57840b41dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('users', 'last_name')


def downgrade() -> None:
    op.add_column('users', sa.Column('last_name', sa.VARCHAR(), autoincrement=False, nullable=True))
