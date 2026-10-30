
from alembic import op

revision = 'eb57840b41dc'
down_revision = 'e7b50e9463a2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f('ix_chats_user_id'), 'chats', ['user_id'], unique=False)
    op.create_index('ix_days_user_id_timestamp', 'days', ['user_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_days_tags_tag_id'), 'days_tags', ['tag_id'], unique=False)
    op.create_index('ix_insights_user_id_timestamp', 'insights', ['user_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_tags_user_id'), 'tags', ['user_id'], unique=False)
    op.create_index(op.f('ix_trackable_items_user_id'), 'trackable_items', ['user_id'], unique=False)
    op.create_index('ix_trackable_progress_user_id_timestamp', 'trackable_progress', ['user_id', 'timestamp'], unique=False)
    op.create_index(op.f('ix_trackable_types_user_id'), 'trackable_types', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_tokens_refresh_token_hash'), 'user_tokens', ['refresh_token_hash'], unique=False)
    op.create_index(op.f('ix_user_tokens_user_id'), 'user_tokens', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_tokens_user_id'), table_name='user_tokens')
    op.drop_index(op.f('ix_user_tokens_refresh_token_hash'), table_name='user_tokens')
    op.drop_index(op.f('ix_trackable_types_user_id'), table_name='trackable_types')
    op.drop_index('ix_trackable_progress_user_id_timestamp', table_name='trackable_progress')
    op.drop_index(op.f('ix_trackable_items_user_id'), table_name='trackable_items')
    op.drop_index(op.f('ix_tags_user_id'), table_name='tags')
    op.drop_index('ix_insights_user_id_timestamp', table_name='insights')
    op.drop_index(op.f('ix_days_tags_tag_id'), table_name='days_tags')
    op.drop_index('ix_days_user_id_timestamp', table_name='days')
    op.drop_index(op.f('ix_chats_user_id'), table_name='chats')
