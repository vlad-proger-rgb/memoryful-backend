from alembic import op
import sqlalchemy as sa


revision = '6b1b9d6d44c8'
down_revision = '2afd5fa8f4a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'workspaces',
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('dashboard_background', sa.String(), nullable=True),
        sa.Column('day_background', sa.String(), nullable=True),
        sa.Column('search_background', sa.String(), nullable=True),
        sa.Column('settings_background', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('workspaces')
