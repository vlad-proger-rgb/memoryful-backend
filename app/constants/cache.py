CACHE_PREFIX = "fastapi-cache"

# Key segment for entries that belong to no single user.
GLOBAL_SCOPE = "global"

# The default key builder repr()s each kwarg, which for injected dependencies bakes in a
# memory address: `db` differs every request, `storage_service` per process restart.
EXCLUDED_CACHE_KWARGS = {"db", "request", "response", "storage_service"}
