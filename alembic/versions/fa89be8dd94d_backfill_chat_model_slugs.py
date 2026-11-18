from alembic import op
import sqlalchemy as sa


revision = 'fa89be8dd94d'
down_revision = 'a4eab891fa17'
branch_labels = None
depends_on = None

# Catalog slugs for the rows that predate them, keyed by their provider model id.
SLUGS_BY_NAME = {
    'gemini-2.5-flash-lite': 'gemini-2.5-flash-lite',
    'gemini-3.1-flash-lite': 'gemini-3.1-flash-lite',
    'claude-haiku-4-5': 'claude-haiku-4.5',
    'xai/grok-4.1-fast-non-reasoning': 'grok-4.1-fast',
    'xai/grok-4.1-fast-reasoning': 'grok-4.1-fast-reasoning',
    'gpt-5.4-nano': 'gpt-5.4-nano',
    'gpt-5.4-mini': 'gpt-5.4-mini',
    'gpt-4o-mini': 'gpt-4o-mini',
}


def upgrade() -> None:
    op.get_bind().execute(
        sa.text('UPDATE chat_models SET slug = :slug WHERE slug IS NULL AND name = :name'),
        [{'name': name, 'slug': slug} for name, slug in SLUGS_BY_NAME.items()],
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text('UPDATE chat_models SET slug = NULL WHERE slug = :slug'),
        [{'slug': slug} for slug in SLUGS_BY_NAME.values()],
    )
