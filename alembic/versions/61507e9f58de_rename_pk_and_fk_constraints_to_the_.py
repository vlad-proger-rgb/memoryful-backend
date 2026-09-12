from alembic import op

revision = "61507e9f58de"
down_revision = "b814cecbec68"
branch_labels = None
depends_on = None

# RENAME CONSTRAINT is metadata-only. Dropping and recreating these would revalidate
# every referencing row and take ACCESS EXCLUSIVE on each table.
#
# Conditional because a database created after the convention landed on Base already has
# the new names: env.py passes Base.metadata, and alembic applies its naming_convention to
# the unnamed constraints in the first revision.
RENAMES = (
    ("chat_models", "chat_models_pkey", "pk_chat_models"),
    ("chats", "chats_model_id_fkey", "fk_chats_model_id_chat_models"),
    ("chats", "chats_user_id_fkey", "fk_chats_user_id_users"),
    ("chats", "chats_pkey", "pk_chats"),
    ("cities", "cities_country_id_fkey", "fk_cities_country_id_countries"),
    ("cities", "cities_pkey", "pk_cities"),
    ("countries", "countries_pkey", "pk_countries"),
    ("days", "days_city_id_fkey", "fk_days_city_id_cities"),
    ("days", "days_user_id_fkey", "fk_days_user_id_users"),
    ("days", "days_pkey", "pk_days"),
    ("days_tags", "days_tags_day_timestamp_user_id_fkey", "fk_days_tags_day_timestamp_days"),
    ("days_tags", "days_tags_tag_id_fkey", "fk_days_tags_tag_id_tags"),
    ("days_tags", "days_tags_pkey", "pk_days_tags"),
    ("insight_types", "insight_types_pkey", "pk_insight_types"),
    ("insights", "insights_insight_type_id_fkey", "fk_insights_insight_type_id_insight_types"),
    ("insights", "insights_model_id_fkey", "fk_insights_model_id_chat_models"),
    ("insights", "insights_timestamp_user_id_fkey", "fk_insights_timestamp_days"),
    ("insights", "insights_user_id_fkey", "fk_insights_user_id_users"),
    ("insights", "insights_pkey", "pk_insights"),
    ("months", "months_user_id_fkey", "fk_months_user_id_users"),
    ("months", "months_pkey", "pk_months"),
    ("search_history", "search_history_user_id_fkey", "fk_search_history_user_id_users"),
    ("search_history", "search_history_pkey", "pk_search_history"),
    ("suggestions", "suggestions_model_id_fkey", "fk_suggestions_model_id_chat_models"),
    ("suggestions", "suggestions_timestamp_user_id_fkey", "fk_suggestions_timestamp_days"),
    ("suggestions", "suggestions_user_id_fkey", "fk_suggestions_user_id_users"),
    ("suggestions", "suggestions_pkey", "pk_suggestions"),
    ("tags", "tags_user_id_fkey", "fk_tags_user_id_users"),
    ("tags", "tags_pkey", "pk_tags"),
    ("trackable_items", "trackable_items_type_id_fkey", "fk_trackable_items_type_id_trackable_types"),
    ("trackable_items", "trackable_items_user_id_fkey", "fk_trackable_items_user_id_users"),
    ("trackable_items", "trackable_items_pkey", "pk_trackable_items"),
    ("trackable_progress", "trackable_progress_timestamp_user_id_fkey", "fk_trackable_progress_timestamp_days"),
    ("trackable_progress", "trackable_progress_trackable_item_id_fkey", "fk_trackable_progress_trackable_item_id_trackable_items"),
    ("trackable_progress", "trackable_progress_user_id_fkey", "fk_trackable_progress_user_id_users"),
    ("trackable_progress", "trackable_progress_pkey", "pk_trackable_progress"),
    ("trackable_types", "trackable_types_user_id_fkey", "fk_trackable_types_user_id_users"),
    ("trackable_types", "trackable_types_pkey", "pk_trackable_types"),
    ("user_tokens", "user_tokens_user_id_fkey", "fk_user_tokens_user_id_users"),
    ("user_tokens", "user_tokens_pkey", "pk_user_tokens"),
    ("users", "users_city_id_fkey", "fk_users_city_id_cities"),
    ("users", "users_country_id_fkey", "fk_users_country_id_countries"),
    ("users", "users_pkey", "pk_users"),
    ("workspace_backgrounds", "workspace_backgrounds_user_id_fkey", "fk_workspace_backgrounds_user_id_users"),
    ("workspace_backgrounds", "workspace_backgrounds_pkey", "pk_workspace_backgrounds"),
)


def _rename_if_present(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = '{old}' AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old} TO {new};
            END IF;
        END $$;
        """  # noqa: S608
    )


def upgrade() -> None:
    for table, old, new in RENAMES:
        _rename_if_present(table, old, new)


def downgrade() -> None:
    for table, old, new in RENAMES:
        _rename_if_present(table, new, old)
