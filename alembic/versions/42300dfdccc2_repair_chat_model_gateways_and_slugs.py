
import sqlalchemy as sa
from alembic import op

revision = '42300dfdccc2'
down_revision = '93aa2c474151'
branch_labels = None
depends_on = None

# fa89be8dd94d's slugs for these differ from the catalog's, so the sync would duplicate them.
CATALOG_SLUGS = {
    'claude-haiku-4.5': 'claude-haiku-4-5',
    'grok-4.1-fast': 'grok-4.1-fast-non-reasoning',
}


def upgrade() -> None:
    # 60db397a6c8b copied provider into gateway; xAI models are only served through Vertex.
    op.execute("UPDATE chat_models SET gateway = 'vertex_maas' WHERE provider = 'xai'")
    op.get_bind().execute(
        sa.text(
            'UPDATE chat_models SET slug = :new WHERE slug = :old'
            ' AND NOT EXISTS (SELECT 1 FROM chat_models WHERE slug = :new)'
        ),
        [{'old': old, 'new': new} for old, new in CATALOG_SLUGS.items()],
    )


def downgrade() -> None:
    pass
