from alembic import op

revision = "61507e9f58de"
down_revision = "b814cecbec68"
branch_labels = None
depends_on = None

# RENAME CONSTRAINT is metadata-only. Dropping and recreating these would revalidate
# every referencing row and take ACCESS EXCLUSIVE on each table.


def upgrade() -> None:
    op.execute("ALTER TABLE chat_models RENAME CONSTRAINT chat_models_pkey TO pk_chat_models")
    op.execute(
        "ALTER TABLE chats RENAME CONSTRAINT chats_model_id_fkey TO fk_chats_model_id_chat_models"
    )
    op.execute("ALTER TABLE chats RENAME CONSTRAINT chats_user_id_fkey TO fk_chats_user_id_users")
    op.execute("ALTER TABLE chats RENAME CONSTRAINT chats_pkey TO pk_chats")
    op.execute(
        "ALTER TABLE cities RENAME CONSTRAINT cities_country_id_fkey TO fk_cities_country_id_countries"
    )
    op.execute("ALTER TABLE cities RENAME CONSTRAINT cities_pkey TO pk_cities")
    op.execute("ALTER TABLE countries RENAME CONSTRAINT countries_pkey TO pk_countries")
    op.execute("ALTER TABLE days RENAME CONSTRAINT days_city_id_fkey TO fk_days_city_id_cities")
    op.execute("ALTER TABLE days RENAME CONSTRAINT days_user_id_fkey TO fk_days_user_id_users")
    op.execute("ALTER TABLE days RENAME CONSTRAINT days_pkey TO pk_days")
    op.execute(
        "ALTER TABLE days_tags RENAME CONSTRAINT days_tags_day_timestamp_user_id_fkey TO fk_days_tags_day_timestamp_days"
    )
    op.execute(
        "ALTER TABLE days_tags RENAME CONSTRAINT days_tags_tag_id_fkey TO fk_days_tags_tag_id_tags"
    )
    op.execute("ALTER TABLE days_tags RENAME CONSTRAINT days_tags_pkey TO pk_days_tags")
    op.execute("ALTER TABLE insight_types RENAME CONSTRAINT insight_types_pkey TO pk_insight_types")
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT insights_insight_type_id_fkey TO fk_insights_insight_type_id_insight_types"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT insights_model_id_fkey TO fk_insights_model_id_chat_models"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT insights_timestamp_user_id_fkey TO fk_insights_timestamp_days"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT insights_user_id_fkey TO fk_insights_user_id_users"
    )
    op.execute("ALTER TABLE insights RENAME CONSTRAINT insights_pkey TO pk_insights")
    op.execute(
        "ALTER TABLE months RENAME CONSTRAINT months_user_id_fkey TO fk_months_user_id_users"
    )
    op.execute("ALTER TABLE months RENAME CONSTRAINT months_pkey TO pk_months")
    op.execute(
        "ALTER TABLE search_history RENAME CONSTRAINT search_history_user_id_fkey TO fk_search_history_user_id_users"
    )
    op.execute(
        "ALTER TABLE search_history RENAME CONSTRAINT search_history_pkey TO pk_search_history"
    )
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT suggestions_model_id_fkey TO fk_suggestions_model_id_chat_models"
    )
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT suggestions_timestamp_user_id_fkey TO fk_suggestions_timestamp_days"
    )
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT suggestions_user_id_fkey TO fk_suggestions_user_id_users"
    )
    op.execute("ALTER TABLE suggestions RENAME CONSTRAINT suggestions_pkey TO pk_suggestions")
    op.execute("ALTER TABLE tags RENAME CONSTRAINT tags_user_id_fkey TO fk_tags_user_id_users")
    op.execute("ALTER TABLE tags RENAME CONSTRAINT tags_pkey TO pk_tags")
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT trackable_items_type_id_fkey TO fk_trackable_items_type_id_trackable_types"
    )
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT trackable_items_user_id_fkey TO fk_trackable_items_user_id_users"
    )
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT trackable_items_pkey TO pk_trackable_items"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT trackable_progress_timestamp_user_id_fkey TO fk_trackable_progress_timestamp_days"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT trackable_progress_trackable_item_id_fkey TO fk_trackable_progress_trackable_item_id_trackable_items"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT trackable_progress_user_id_fkey TO fk_trackable_progress_user_id_users"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT trackable_progress_pkey TO pk_trackable_progress"
    )
    op.execute(
        "ALTER TABLE trackable_types RENAME CONSTRAINT trackable_types_user_id_fkey TO fk_trackable_types_user_id_users"
    )
    op.execute(
        "ALTER TABLE trackable_types RENAME CONSTRAINT trackable_types_pkey TO pk_trackable_types"
    )
    op.execute(
        "ALTER TABLE user_tokens RENAME CONSTRAINT user_tokens_user_id_fkey TO fk_user_tokens_user_id_users"
    )
    op.execute("ALTER TABLE user_tokens RENAME CONSTRAINT user_tokens_pkey TO pk_user_tokens")
    op.execute("ALTER TABLE users RENAME CONSTRAINT users_city_id_fkey TO fk_users_city_id_cities")
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT users_country_id_fkey TO fk_users_country_id_countries"
    )
    op.execute("ALTER TABLE users RENAME CONSTRAINT users_pkey TO pk_users")
    op.execute(
        "ALTER TABLE workspace_backgrounds RENAME CONSTRAINT workspace_backgrounds_user_id_fkey TO fk_workspace_backgrounds_user_id_users"
    )
    op.execute(
        "ALTER TABLE workspace_backgrounds RENAME CONSTRAINT workspace_backgrounds_pkey TO pk_workspace_backgrounds"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE workspace_backgrounds RENAME CONSTRAINT pk_workspace_backgrounds TO workspace_backgrounds_pkey"
    )
    op.execute(
        "ALTER TABLE workspace_backgrounds RENAME CONSTRAINT fk_workspace_backgrounds_user_id_users TO workspace_backgrounds_user_id_fkey"
    )
    op.execute("ALTER TABLE users RENAME CONSTRAINT pk_users TO users_pkey")
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT fk_users_country_id_countries TO users_country_id_fkey"
    )
    op.execute("ALTER TABLE users RENAME CONSTRAINT fk_users_city_id_cities TO users_city_id_fkey")
    op.execute("ALTER TABLE user_tokens RENAME CONSTRAINT pk_user_tokens TO user_tokens_pkey")
    op.execute(
        "ALTER TABLE user_tokens RENAME CONSTRAINT fk_user_tokens_user_id_users TO user_tokens_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_types RENAME CONSTRAINT pk_trackable_types TO trackable_types_pkey"
    )
    op.execute(
        "ALTER TABLE trackable_types RENAME CONSTRAINT fk_trackable_types_user_id_users TO trackable_types_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT pk_trackable_progress TO trackable_progress_pkey"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT fk_trackable_progress_user_id_users TO trackable_progress_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT fk_trackable_progress_trackable_item_id_trackable_items TO trackable_progress_trackable_item_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_progress RENAME CONSTRAINT fk_trackable_progress_timestamp_days TO trackable_progress_timestamp_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT pk_trackable_items TO trackable_items_pkey"
    )
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT fk_trackable_items_user_id_users TO trackable_items_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE trackable_items RENAME CONSTRAINT fk_trackable_items_type_id_trackable_types TO trackable_items_type_id_fkey"
    )
    op.execute("ALTER TABLE tags RENAME CONSTRAINT pk_tags TO tags_pkey")
    op.execute("ALTER TABLE tags RENAME CONSTRAINT fk_tags_user_id_users TO tags_user_id_fkey")
    op.execute("ALTER TABLE suggestions RENAME CONSTRAINT pk_suggestions TO suggestions_pkey")
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT fk_suggestions_user_id_users TO suggestions_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT fk_suggestions_timestamp_days TO suggestions_timestamp_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE suggestions RENAME CONSTRAINT fk_suggestions_model_id_chat_models TO suggestions_model_id_fkey"
    )
    op.execute(
        "ALTER TABLE search_history RENAME CONSTRAINT pk_search_history TO search_history_pkey"
    )
    op.execute(
        "ALTER TABLE search_history RENAME CONSTRAINT fk_search_history_user_id_users TO search_history_user_id_fkey"
    )
    op.execute("ALTER TABLE months RENAME CONSTRAINT pk_months TO months_pkey")
    op.execute(
        "ALTER TABLE months RENAME CONSTRAINT fk_months_user_id_users TO months_user_id_fkey"
    )
    op.execute("ALTER TABLE insights RENAME CONSTRAINT pk_insights TO insights_pkey")
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT fk_insights_user_id_users TO insights_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT fk_insights_timestamp_days TO insights_timestamp_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT fk_insights_model_id_chat_models TO insights_model_id_fkey"
    )
    op.execute(
        "ALTER TABLE insights RENAME CONSTRAINT fk_insights_insight_type_id_insight_types TO insights_insight_type_id_fkey"
    )
    op.execute("ALTER TABLE insight_types RENAME CONSTRAINT pk_insight_types TO insight_types_pkey")
    op.execute("ALTER TABLE days_tags RENAME CONSTRAINT pk_days_tags TO days_tags_pkey")
    op.execute(
        "ALTER TABLE days_tags RENAME CONSTRAINT fk_days_tags_tag_id_tags TO days_tags_tag_id_fkey"
    )
    op.execute(
        "ALTER TABLE days_tags RENAME CONSTRAINT fk_days_tags_day_timestamp_days TO days_tags_day_timestamp_user_id_fkey"
    )
    op.execute("ALTER TABLE days RENAME CONSTRAINT pk_days TO days_pkey")
    op.execute("ALTER TABLE days RENAME CONSTRAINT fk_days_user_id_users TO days_user_id_fkey")
    op.execute("ALTER TABLE days RENAME CONSTRAINT fk_days_city_id_cities TO days_city_id_fkey")
    op.execute("ALTER TABLE countries RENAME CONSTRAINT pk_countries TO countries_pkey")
    op.execute("ALTER TABLE cities RENAME CONSTRAINT pk_cities TO cities_pkey")
    op.execute(
        "ALTER TABLE cities RENAME CONSTRAINT fk_cities_country_id_countries TO cities_country_id_fkey"
    )
    op.execute("ALTER TABLE chats RENAME CONSTRAINT pk_chats TO chats_pkey")
    op.execute("ALTER TABLE chats RENAME CONSTRAINT fk_chats_user_id_users TO chats_user_id_fkey")
    op.execute(
        "ALTER TABLE chats RENAME CONSTRAINT fk_chats_model_id_chat_models TO chats_model_id_fkey"
    )
    op.execute("ALTER TABLE chat_models RENAME CONSTRAINT pk_chat_models TO chat_models_pkey")
