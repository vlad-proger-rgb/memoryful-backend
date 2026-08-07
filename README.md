# Memoryful Backend

FastAPI backend for Memoryful - Your AI-Powered Life Journal and Analysis Platform

## Overview

Memoryful is an intelligent life journaling platform that combines personal data recording with AI-powered analysis to provide meaningful insights and recommendations for life improvement. The backend serves as the core engine, handling data processing, AI analysis, and integration with various external services.

## Features

### Core Functionality

- **Life Journaling**: Record and organize daily experiences, memories, and activities
- **AI-Powered Analysis**: Automated insights and recommendations using MemoryfulAI
- **External Service Integration**: Seamless connection with health, gaming, and location services
- **Smart Search**: Natural language queries about your life events and patterns
- **Secure Authentication**: JWT-based authentication with email verification

### Data Structure

- **Months**: Track monthly summaries with descriptions and highlights
- **Days**: Detailed daily entries including:
  - Descriptions and content
  - Location data (country/city)
  - Learning progress
  - Custom tags
  - Photo attachments
  - Integration data

### AI Analysis Types

- **Daily Analysis**: Quick insights and notes
- **Weekly Analysis**: Trend identification and pattern recognition
- **Monthly Analysis**: Comprehensive summaries and statistics
- **Yearly Analysis**: Long-term insights and achievements

## Tech Stack

### Backend

- **Framework**: FastAPI
- **Database**: PostgreSQL with Async SQLAlchemy 2.0
- **Caching**: Redis
- **Message Broker**: GCP Pub/Sub (emulator locally)
- **Task Queue**: Celery
- **Authentication**: JWT (Access + Refresh tokens)
- **API Documentation**: OpenAPI/Swagger

### External Integrations

- Samsung Health (steps and activity data)
- Gaming platforms (Steam, Epic Games, EA)
- Google APIs (location and purchase history)
- Mobile gaming platforms

## Project Structure

```bash
memoryful-backend/
├── app/
│   ├── core/                      # Core functionality
│   ├── routers/                   # API endpoints
│   ├── models/                    # Database models
│   ├── schemas/                   # Pydantic schemas
│   ├── tasks/                     # Celery tasks
│   ├── templates/                 # HTML templates (e.g. for email notifications)
│   ├── init_db.py                 # Database initialization script
│   └── main.py                    # FastAPI application entry point
├── docker/
│   ├── Dockerfile                 # Production container definition
│   ├── Dockerfile.dev             # Development container definition
│   ├── Dockerfile.celery          # Celery worker container definition
│   ├── docker-compose.local.yml   # Local development orchestration
│   ├── docker-compose.vm.yml      # VM production orchestration
│   └── init-restore-db.sh         # Restores the latest prod dump on a fresh DB volume for local setup
├── scripts/
│   ├── deploy-app.sh              # VM deployment script
│   └── python/
│       └── manage_backup.py       # Dump prod DB / restore into the local one
├── backups/                       # Local prod DB dumps (gitignored)
├── bucket_base/                   # Default assets seeded into local MinIO (gitignored)
├── specs/                         # Deep-dives kept out of the README
├── .env.local                     # Local development environment variables
├── .env.prod                      # Production environment template
├── .gitignore                     # Git ignore rules
├── mypy.ini                       # MyPy type checking configuration
├── requirements.txt               # Python dependencies
├── requirements.dev.txt           # Development dependencies
└── README.md                      # Project documentation
```

## Setup and Installation

### Prerequisites

- Docker
- Docker Compose

### Environment Configurations

This project supports two distinct environments:

#### **Local Development** (`.env.local`)

- All services run locally in Docker containers
- No external dependencies or cloud services
- Uses local PostgreSQL, Redis, Pub/Sub emulator, MinIO, Ollama
- Perfect for development and testing

#### **Production** (`.env.prod`)

- Runs FastAPI, nginx, and Celery worker on a Compute Engine VM
- Uses Neon Postgres, GCP Pub/Sub, GCS-compatible storage, and Redis/Upstash
- Secrets managed via GCP Secret Manager
- Deployed with the unified VM Docker Compose stack

### Development Setup

#### 1. Clone the repository

```bash
git clone https://github.com/vlad-proger-rgb/memoryful-backend.git
cd memoryful-backend
```

#### 2. Start with docker-compose

- Local:

```bash
docker-compose -p memoryful -f docker/docker-compose.local.yml --env-file=.env.local up --build
```

- Production VM stack:

```bash
# First, create .env from template
cp .env.prod .env
# Edit .env with your actual values, then run:
docker-compose -p memoryful -f docker/docker-compose.vm.yml --env-file=.env up --build
```

### Working with Production Data (Dev DB Workflow)

There are three env files, and it matters which one Docker Compose loads:

| File | Used for |
| --- | --- |
| `.env.local` | The full local stack (local Postgres, Redis, MinIO, Ollama, …). Committed with placeholders — never put real secrets here. |
| `.env.local.secrets` | Your real container overrides (API keys, `LLM_MODE=vertex`). Gitignored; loaded after `.env.local` so it wins. Copy from `.env.local.secrets.example`. |
| `.env` | Host tooling only — just `BACKUP_SOURCE_URL` (the Neon URL) for `manage_backup.py`. Gitignored; never loaded into a container. |
| `.env.prod` | Template for the VM deploy; the VM keeps its own filled-in `.env`. |

> **Real keys go in `.env.local.secrets`, never in `.env.local`.** `.env.local` is
> committed with placeholders, so you never have to revert it before a commit —
> your real OpenAI/Anthropic keys and `LLM_MODE=vertex` live only in the gitignored
> override file, which Docker Compose loads second (later file wins). A fresh clone
> with no override file just runs on the placeholders (Ollama). The `BACKUP_SOURCE_URL`
> for the backup script stays in `.env` on purpose — it's your **production DB**
> connection string, read by a host script, and should never be injected into the
> app container the way `.env.local.secrets` is.

Set it up once, then fill only the lines you need:

```bash
cp .env.local.secrets.example .env.local.secrets
```

Fill the real keys from your password manager. Delete a line rather than leaving
it blank — an empty value overrides the `.env.local` placeholder with an empty
string. Drop `LLM_MODE=vertex` to stay on local Ollama.

> ⚠️ **Always pass `--env-file` explicitly.** Docker Compose auto-loads a bare
> `.env` for `${VAR}` interpolation in the compose file — and that file is *not*
> the local config. Without `--env-file .env.local`, compose-level variables such
> as the Redis container's `--requirepass ${REDIS_PASSWORD}` resolve to empty
> while the app reads the real value from `.env.local`, so the app cannot
> authenticate → `invalid username-password pair`. Always name the file:
>
> ```bash
> docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml up --build
> ```

#### Local stack with restored prod data

Work against a **local copy** of production data. Safe: nothing you do touches
the real database.

```bash
# 1. One-time: put the Neon connection string in .env
#    BACKUP_SOURCE_URL=postgresql://USER:PASS@HOST/neondb?sslmode=require

# 2. Dump prod -> backups/neondb_backup_latest.dump (+ a timestamped copy).
#    Postgres client tools run inside a Docker image; nothing to install locally.
python scripts/python/manage_backup.py backup

# 3a. Load it into the ALREADY-RUNNING local DB container (no wipe):
python scripts/python/manage_backup.py restore

# 3b. …or reset from scratch. On a fresh volume the DB auto-restores the latest
#     dump via docker/init-restore-db.sh (runs only when the volume is empty):
docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml down -v
docker compose -p memoryful --env-file .env.local -f docker/docker-compose.local.yml up --build
```

Local file storage (MinIO) seeds itself: the `minio-init` service creates the
`memoryful` bucket and mirrors default workspace assets from `bucket_base/` on
every `up` (idempotent). Real user photos are **not** copied — they stay in prod
GCS, so restored days with photos will show broken image links locally. That's
expected and intentional (mirroring them would be gigabytes).

`bucket_base/` is gitignored, so a fresh machine needs the default assets pulled
from the public bucket before that seeding has anything to mirror:

```bash
gcloud storage rsync -r gs://memoryful-public/users/defaults bucket_base/users/defaults
```

See [specs/workspace-backgrounds.md](specs/workspace-backgrounds.md) for how
backgrounds are stored, resolved and encoded.

Re-run `backup` whenever you want to refresh from prod (e.g. before testing a new
migration). Dumps live in `backups/` (gitignored). The dump's Postgres major must
match the local DB, so keep these aligned with Neon (currently **18**): `PG_IMAGE`
in `scripts/python/manage_backup.py` and the `db` image in
`docker/docker-compose.local.yml`. After changing the `db` image, wipe the volume
(`down -v`) so it re-initialises on the new major.

### Local AI Model (Ollama)

The local AI features — day **insights** and **suggestions** — are generated by an LLM
served from the bundled `ollama` container (`memoryful-ollama-local`). This path is used
whenever `LLM_MODE=local`, which is the default in `.env.local`.

Ollama ships **without any model preinstalled**. Models are downloaded on demand and stored
in the `ollama_data_local` Docker volume, so they normally persist across restarts. If that
volume is removed — or you delete the model manually to free up disk space — you must pull
it again before AI generation will work. Until then, requests fail with:

```text
Local model not found in Ollama. Requested LOCAL_LLM_MODEL='llama3.1'. ...
```

#### Relevant settings (`.env.local`)

| Variable             | Default                     | Purpose                                              |
| -------------------- | --------------------------- | ---------------------------------------------------- |
| `LLM_MODE`           | `local`                     | Gateway: `local` (Ollama) or `vertex` (GCP models).  |
| `LOCAL_LLM_MODEL`    | `llama3.1`                  | Ollama model tag to run (this is what you must pull).|
| `LOCAL_LLM_BASE_URL` | `http://ollama:11434/v1`    | OpenAI-compatible endpoint (Docker-internal host).   |
| `LOCAL_LLM_API_KEY`  | `local`                     | Placeholder key; Ollama ignores it.                  |

#### 1. Make sure the Ollama container is running

If the full stack is already up (from the setup step above), Ollama is running. To start
just this one service:

```bash
docker-compose -p memoryful -f docker/docker-compose.local.yml --env-file=.env.local up -d ollama
```

#### 2. Pull the model

Download the model named in `LOCAL_LLM_MODEL` (default `llama3.1`, ~4.7 GB) into the container.
The download persists in the `ollama_data_local` volume:

```bash
docker exec -it memoryful-ollama-local ollama pull llama3.1
```

#### 3. Verify it's installed

```bash
docker exec -it memoryful-ollama-local ollama list
```

You should see `llama3.1` in the list.

#### 4. (Optional) Test generation

From the host (the container's port `11434` is published):

```bash
curl http://localhost:11434/api/generate -d '{"model": "llama3.1", "prompt": "Say hi", "stream": false}'
```

A JSON response with a `"response"` field means the model is serving correctly. Insights and
suggestions should now generate again — no app restart is required after pulling.

#### Using a different model

Pick any tag from the [Ollama library](https://ollama.com/library), then keep the pulled
model and the config in sync:

```bash
# 1. Pull the model you want, e.g. a smaller one for low-RAM / CPU machines
docker exec -it memoryful-ollama-local ollama pull llama3.2:3b

# 2. Set LOCAL_LLM_MODEL=llama3.2:3b in .env.local

# 3. Restart the app so it picks up the new env value
docker-compose -p memoryful -f docker/docker-compose.local.yml --env-file=.env.local up -d app
```

#### Notes

- **GPU**: the `ollama` service in `docker-compose.local.yml` reserves an NVIDIA GPU. On a
  machine without one (or without the NVIDIA Container Toolkit), remove the `deploy.resources`
  block from the `ollama` service — Ollama will fall back to CPU (slower, but works).
- **Disk**: models live in the `ollama_data_local` volume. `docker-compose ... down -v` deletes
  it (and all other data volumes), which is what forces a re-pull.

### Production Setup

For production, you'll need to set up the following:

1. Create a GCP project and enable the necessary APIs
2. Set up GCP Pub/Sub and storage
3. Create secrets in GCP Secret Manager
4. Set up Neon Postgres
5. Set up Redis (e.g., Upstash Redis with free tier)
6. Deploy the unified VM stack

### GCP Secrets

Store these in GCP Secret Manager for production:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `REDIS_HOST`
- `REDIS_PASSWORD`
- `ACCESS_SECRET_KEY`
- `REFRESH_SECRET_KEY`
- `RESEND_API_KEY`
- `MAIL_FROM`
- `S3_ACCESS_KEY_ID` (for GCS)
- `S3_SECRET_ACCESS_KEY` (for GCS)
- `OPENAI_API_KEY` (if using OpenAI)
- `ANTHROPIC_API_KEY` (if using Anthropic)

## API Documentation

Once the server is running, access the API documentation at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Status

This project is currently under active development. The backend is being developed as a solo project, focusing on creating a robust and scalable architecture that can support the complex requirements of the Memoryful platform.
