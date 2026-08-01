"""workspace backgrounds: one row per customized page

Replaces the per-page columns on `workspaces` with a `workspace_backgrounds` row
per page the user actually customized. Adding a page now needs no migration, and
each row carries its own blurred placeholder.

`workspaces` is dropped without migrating rows: the app deleted a workspace row
once its last background was cleared, so the table only ever held rows for users
with a custom background — and there are none.

Revision ID: f6a2b8d4c1e3
Revises: d4e3f9a5b2c8
"""

from alembic import op
import sqlalchemy as sa


revision = "f6a2b8d4c1e3"
down_revision = "d4e3f9a5b2c8"
branch_labels = None
depends_on = None

# The pages `workspaces` had when it was dropped, for downgrade only.
LEGACY_PAGES = ("dashboard", "day", "search", "settings")


def upgrade() -> None:
    op.create_table(
        "workspace_backgrounds",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("page", sa.String(), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False),
        sa.Column("placeholder", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "page"),
    )
    op.drop_table("workspaces")


def downgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        *[sa.Column(f"{page}_background", sa.String(), nullable=True) for page in LEGACY_PAGES],
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.drop_table("workspace_backgrounds")
