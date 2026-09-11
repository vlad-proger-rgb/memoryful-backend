"""fold suggestions into insights by kind

Revision ID: a1f4c7d2e903
Revises: 61507e9f58de

`suggestions` and `insights` held the same columns and `insight_types` never had more than
one row, so the two tables become one discriminated by `kind`. Suggestion rows keep their
ids when they move across, and `suggestions.date` becomes their `created_at`.

`insights.date_begin` goes with them: it restated the day the row already points at, and
drifted from it once a day was edited.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1f4c7d2e903"
down_revision = "61507e9f58de"
branch_labels = None
depends_on = None

MOVED_COLUMNS = "id, user_id, model_id, timestamp, description, icon, content"

insight_kind = postgresql.ENUM("observation", "suggestion", name="insightkind", create_type=False)


def upgrade() -> None:
    # Before the insert, or its NOT NULL rejects every incoming suggestion row.
    op.drop_constraint(
        op.f("fk_insights_insight_type_id_insight_types"), "insights", type_="foreignkey"
    )
    op.drop_column("insights", "insight_type_id")
    op.drop_column("insights", "date_begin")

    insight_kind.create(op.get_bind(), checkfirst=True)
    op.add_column("insights", sa.Column("kind", insight_kind, nullable=True))
    op.execute("UPDATE insights SET kind = 'observation'")
    op.alter_column("insights", "kind", nullable=False)

    op.execute(
        f"INSERT INTO insights ({MOVED_COLUMNS}, created_at, kind) "  # noqa: S608
        f"SELECT {MOVED_COLUMNS}, date::timestamptz, 'suggestion'::insightkind FROM suggestions"
    )

    op.drop_table("suggestions")
    op.drop_table("insight_types")


def downgrade() -> None:
    op.create_table(
        "insight_types",
        sa.Column("name", sa.VARCHAR(), nullable=False),
        sa.Column("duration", postgresql.INTERVAL(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_insight_types")),
    )
    op.execute(
        "INSERT INTO insight_types (id, name, duration) "
        "VALUES (gen_random_uuid(), 'daily', INTERVAL '1 day')"
    )

    op.create_table(
        "suggestions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("model_id", sa.UUID(), nullable=False),
        sa.Column("timestamp", sa.INTEGER(), nullable=False),
        sa.Column("date", sa.DATE(), nullable=False),
        sa.Column("description", sa.VARCHAR(), nullable=False),
        sa.Column("icon", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("content", sa.VARCHAR(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["model_id"], ["chat_models.id"], name=op.f("fk_suggestions_model_id_chat_models")
        ),
        sa.ForeignKeyConstraint(
            ["timestamp", "user_id"],
            ["days.timestamp", "days.user_id"],
            name=op.f("fk_suggestions_timestamp_days"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_suggestions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestions")),
    )
    op.execute(
        f"INSERT INTO suggestions ({MOVED_COLUMNS}, date) "  # noqa: S608
        f"SELECT {MOVED_COLUMNS}, created_at::date FROM insights WHERE kind = 'suggestion'"
    )
    op.execute("DELETE FROM insights WHERE kind = 'suggestion'")

    op.add_column("insights", sa.Column("date_begin", sa.DATE(), nullable=True))
    op.execute("UPDATE insights SET date_begin = to_timestamp(timestamp)::date")
    op.alter_column("insights", "date_begin", nullable=False)

    op.add_column("insights", sa.Column("insight_type_id", sa.UUID(), nullable=True))
    op.execute("UPDATE insights SET insight_type_id = (SELECT id FROM insight_types LIMIT 1)")
    op.alter_column("insights", "insight_type_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_insights_insight_type_id_insight_types"),
        "insights",
        "insight_types",
        ["insight_type_id"],
        ["id"],
    )

    op.drop_column("insights", "kind")
    insight_kind.drop(op.get_bind(), checkfirst=True)
