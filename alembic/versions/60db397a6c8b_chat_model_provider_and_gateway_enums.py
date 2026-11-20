
from alembic import op
import sqlalchemy as sa


revision = '60db397a6c8b'
down_revision = '1aa3afe9bc34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Models retired before gateways existed were all on their provider's own API.
    op.execute("UPDATE chat_models SET gateway = provider WHERE gateway IS NULL")
    op.alter_column('chat_models', 'provider',
               existing_type=sa.VARCHAR(),
               type_=sa.String(length=32),
               existing_nullable=False)
    op.alter_column('chat_models', 'gateway',
               existing_type=sa.VARCHAR(),
               type_=sa.String(length=32),
               nullable=False)


def downgrade() -> None:
    op.alter_column('chat_models', 'gateway',
               existing_type=sa.String(length=32),
               type_=sa.VARCHAR(),
               nullable=True)
    op.alter_column('chat_models', 'provider',
               existing_type=sa.String(length=32),
               type_=sa.VARCHAR(),
               existing_nullable=False)
