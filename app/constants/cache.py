CACHE_PREFIX = "fastapi-cache"

# Key segment for entries that belong to no single user.
GLOBAL_SCOPE = "global"

# The default key builder repr()s each kwarg, which for injected dependencies bakes in a
# memory address: `db` differs every request, `storage_service` per process restart.
EXCLUDED_CACHE_KWARGS = {"db", "request", "response", "storage_service"}

# TTLs in seconds.
CACHE_TTL_STATIC = 60 * 60 * 6  # global reference data: countries, cities, chat models
CACHE_TTL_USER_DATA = (
    60 * 5
)  # small per-user data mutable via API: tags, trackable types, workspace
CACHE_TTL_DAYS = 60 * 10  # days / months
CACHE_TTL_AI_CONTENT = 60 * 60 * 24  # AI-generated insights/suggestions, immutable once generated
CACHE_TTL_CHAT_HOT = 60 * 60  # hot chat cache (write-through; DB remains source of truth)
