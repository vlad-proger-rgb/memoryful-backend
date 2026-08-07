# memoryful-backend

FastAPI + async SQLAlchemy 2.0 + Celery. Runs entirely in Docker locally; the host has a
`.venv` for tooling only. Python 3.13.

## Commands

Everything runs against the local compose project. **Always name the env file explicitly.**

```bash
# start / rebuild the stack (from this directory)
docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml up --build

# one service
docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml up -d app

# typecheck (strict; covers app/ and mcp_server/)
docker exec memoryful-app-local mypy

# MCP server tests
docker exec memoryful-mcp-local pytest

# autogenerate a migration — inside the container, so the DB URL and driver match
docker exec memoryful-app-local alembic revision --autogenerate -m "name"

# apply it — restart the app container; its command runs `alembic upgrade head` on boot
docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml restart app
```

Containers: `memoryful-{app,mcp,db,redis,celery,minio,ollama,pubsub}-local`.
Swagger at `http://localhost:8000/docs`. MinIO console at `:9001`.
Celery brokers through Pub/Sub everywhere — the emulator locally, the real service in prod.
The local DB is published on **5444**, not 5432.

**Lint and format with `ruff`** — it replaces black, isort and flake8. `ruff format` for
layout, `ruff check --fix` for imports and lint. A hook runs both on edit. Config is in
`pyproject.toml`: line length **100**, and pycodestyle (`E`/`W`) deliberately not selected —
the formatter owns layout, and `E402`/`E712` misfire on deferred model imports and
SQLAlchemy filters like `Model.is_deleted == False`, where `not Model.is_deleted` would
silently change the SQL.

`app/` has no test suite — only `mcp_server/` does, which uses `respx` to mock the API at the
httpx layer. There's an open task to build one for the core app.

## Conventions

- **`Msg[T]` envelope on every *success* response** — `code`, `msg`, `data`. Never a bare model.
  Errors are a different shape: `HTTPException` and the handlers in `app/core/exceptions.py`
  both return `{"detail": "..."}`. So the frontend sees two response shapes, and anything
  parsing responses must handle both. (Worth keeping in mind for the planned i18n keys —
  the error path has no `msg` field to carry one today.)
- **The wire format is camelCase.** Schemas inherit `CamelModel` from `fastapi_camelcase`,
  so `is_new_user` serializes as `isNewUser`. `Msg` itself is a plain `BaseModel`, so
  `code`/`msg`/`data` stay as-is. Python-side code always uses snake_case; only the JSON
  differs. A new schema that forgets `CamelModel` silently breaks the frontend contract.
- **Routers are thin.** No service layer: routers build SQLAlchemy statements directly and
  `await db.commit()` themselves. Match that; don't introduce a repository layer.
- **`Depends(get_current_user())`** — note the call. It yields a `UUID`.
- **Every statement filters on `user_id`.** That is the whole tenancy boundary, on writes
  as much as reads. `update(...).where(Model.id == id)` without `user_id` is a data leak.
- mypy is strict (`disallow_untyped_defs`, `warn_return_any`, `warn_unreachable`).
  Annotate everything, including decorators' targets.
- **Modern typing only.** Built-in generics (`list[T]`, `dict[K, V]`, `tuple[...]`,
  `type[T]`) and `X | None` — never `typing.List`, `typing.Dict`, or `Optional[X]`.
  `typing` is still the right import for `Annotated`, `Literal`, `Protocol`, `TypeVar`,
  `AsyncIterator` and friends.
- New router = two edits in `app/main.py`: the import block and `include_router`.
  Forgetting the second gives a silent 404.

## How things work (not bugs — don't "fix" these)

- **Cache invalidation crosses namespaces.** Reads use `@cached(namespace=...)`; a write
  must `clear_cache()` every namespace whose payload *embeds* the changed object, not just
  its own. Tags live inside day payloads, so `tags.py` clears `tags`, `days_list` and
  `days_detail`. Symptom of missing one: DB is right, UI is stale until the TTL expires.
- **Migrations apply on container start, not on hot-reload.** The compose `command:` is
  `alembic upgrade head && uvicorn ... --reload`. That chain runs once, when the container
  boots. `--reload` only restarts the uvicorn process when a file changes — it never re-runs
  the chain, so a newly generated revision sits unapplied until you
  `restart app`. (`run_migrations()` in `app/main.py` is commented out precisely because
  compose owns this.) Corollary: a broken migration *is* a boot failure — `&&` means uvicorn
  never starts, and the app container dies on startup with the Alembic error in its logs.
- **Three env files, and which one loads matters.** `.env.local` is committed with
  placeholders. `.env.local.secrets` is gitignored and loaded second by `env_file:`, so it
  wins — real keys go there, never in `.env.local`. A blank value in it *overrides* the
  placeholder with an empty string; delete the line instead. `.env` is host-tooling only and
  holds the **production** `BACKUP_SOURCE_URL` — never let compose load it.
- **Ollama is legacy and mostly unused.** AI now routes through Vertex (Gemini/Grok) and
  LangChain (Anthropic/OpenAI), set by `LLM_MODE` in `.env.local.secrets`. The `ollama`
  container still starts, but nothing depends on it unless `LLM_MODE=local` — which needs a
  manual `docker exec -it memoryful-ollama-local ollama pull llama3.1` (~4.7 GB) first.
  Don't propose pulling models as a fix unless local mode is explicitly the goal.
- **Cached routes must exclude non-serializable dependencies.** `cache_key_builder` drops
  `_EXCLUDED_CACHE_KWARGS = {db, request, response, storage_service}` because the default
  builder `repr()`s them and bakes in a memory address. Add a new injected dependency to a
  `@cached` route without adding it to that set and the key changes every request — the
  cache silently never hits, with no error anywhere.
- **MCP tools are deliberately re-loaded per request** (`app/ai/mcp.py`). Don't "optimize" by
  caching the tool objects — `langchain-mcp-adapters` bakes the user's bearer into each tool
  at load time, so a shared cache would call the MCP server as the wrong user.
- **`statement_cache_size: 0`** in the engine's `connect_args` is required by Neon's pooled
  endpoint — PgBouncer transaction pooling is incompatible with asyncpg's prepared-statement
  cache. Removing it breaks production and nothing local.
- **Postgres major must match** between the dump and the `db` image (currently **18**) —
  `PG_IMAGE` in `scripts/python/manage_backup.py` and the `db` image in the local compose file.
- `mcp_server/` is a standalone read-only MCP server over the same API, with its own
  `.env`, `requirements.mcp.txt` and pytest suite. New read endpoints usually want a tool there.

## Known defects

Tracked in the **Claude Backlog** column of the TickTick board, not here — this repo is
public, and a tidy list of unfixed issues in a live service is a roadmap for the wrong
reader. Query that column before assuming any surprising behavior is intended; several
things that look like design choices are open tasks with write-ups.

## Rules

- **Commit only when asked** — then write the message yourself and commit. See the commit
  convention in the workspace root `CLAUDE.md`.
- **Running against production is off limits**: `docker-compose.vm.yml`,
  `scripts/deploy-app.sh`, `gcloud`, anything pointing at Neon. Local work uses a restored
  *copy* — see `/db-refresh`. `.env.prod` itself is ordinary non-secret config and should be
  updated alongside `.env.local` when a new setting is added; real secrets come from GCP
  Secret Manager on the VM.
- Never hand-edit `alembic/versions/`; generate a new revision.
