"""Backup the production (Neon) database and restore it into the local dev DB.

The goal: work against a *local copy* of real prod data instead of hitting the
live database. Dumps land in ./backups (gitignored); restore loads the latest
one into the local Postgres container from docker-compose.local.yml.

Postgres client tools run inside a `postgres` Docker image, so nothing needs to
be installed on the host. Docker must be running.

Prod credentials live in Secret Manager, not in .env — so the source database is
given as a full connection URL (from the Neon dashboard), via --url or the
BACKUP_SOURCE_URL env var.

Usage (run from memoryful-backend/):
    # 1. Dump prod -> backups/neondb_backup_latest.dump (+ a timestamped copy)
    python scripts/python/manage_backup.py backup --url "postgresql://USER:PASS@HOST/neondb?sslmode=require"
    python scripts/python/manage_backup.py backup   # if BACKUP_SOURCE_URL is set

    # 2. Restore the latest dump into the running local DB container
    #    (start it first: docker compose --env-file .env.local -f docker/docker-compose.local.yml up -d db)
    python scripts/python/manage_backup.py restore
    python scripts/python/manage_backup.py restore --backup backups/neondb_backup_20260723.dump
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

# Lets the ✓ and » output survive a non-UTF-8 console.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKUPS_DIR = REPO_ROOT / "backups"

PG_IMAGE = "postgres:18"
LOCAL_DB_CONTAINER = "memoryful-db-local"
LATEST_DUMP = "neondb_backup_latest.dump"


def _mask(text: str) -> str:
    """Redact the password in a postgres URL so it never lands in logs/output."""
    return re.sub(r"(://[^:/@\s]+:)[^@/\s]+(@)", r"\1***\2", text)


def _run(cmd: list[str], **kwargs: Any) -> None:
    print("»", " ".join(_mask(c) for c in cmd))
    subprocess.run(cmd, check=True, **kwargs)  # noqa: S603  # argv list built in this module, never shell-interpolated


def _source_url(cli_url: str | None) -> str:
    """--url wins, then a shell env var, then BACKUP_SOURCE_URL in .env / .env.prod."""
    if cli_url:
        return cli_url
    sources = (
        os.environ,
        dotenv_values(REPO_ROOT / ".env"),
        dotenv_values(REPO_ROOT / ".env.prod"),
    )
    for src in sources:
        url = src.get("BACKUP_SOURCE_URL")
        if url:
            return url
    sys.exit(
        'No source database URL. Pass --url "postgresql://..." or set '
        "BACKUP_SOURCE_URL in .env (get it from the Neon dashboard)."
    )


def backup(args: argparse.Namespace) -> None:
    BACKUPS_DIR.mkdir(exist_ok=True)
    url = _source_url(args.url)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped = f"neondb_backup_{ts}.dump"

    # pg_dump runs inside the postgres image; ./backups is mounted at /backups.
    # -Fc = compressed custom format (restore is version-tolerant and selective).
    _run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{BACKUPS_DIR}:/backups",
            PG_IMAGE,
            "pg_dump",
            url,
            "-Fc",
            "--no-owner",
            "--no-privileges",
            "-f",
            f"/backups/{timestamped}",
        ]
    )

    # Update the "latest" pointer the restore command and init script use.
    # copy2 streams the file instead of loading the whole dump into memory.
    shutil.copy2(BACKUPS_DIR / timestamped, BACKUPS_DIR / LATEST_DUMP)
    print(f"\n✓ Backup written: backups/{timestamped}")
    print(f"✓ Latest updated: backups/{LATEST_DUMP}")


def restore(args: argparse.Namespace) -> None:
    env = dotenv_values(REPO_ROOT / ".env.local")
    user = env.get("POSTGRES_USER") or "main_user"
    db = env.get("POSTGRES_DB") or "main_database"

    dump_name = Path(args.backup).name if args.backup else LATEST_DUMP
    if not (BACKUPS_DIR / dump_name).exists():
        sys.exit(f"Dump not found: backups/{dump_name}. Run `backup` first.")

    print(f"Restoring backups/{dump_name} -> {LOCAL_DB_CONTAINER} ({db}) ...")
    # --clean --if-exists drops existing objects first so restore is idempotent.
    _run(
        [
            "docker",
            "exec",
            LOCAL_DB_CONTAINER,
            "pg_restore",
            "-U",
            user,
            "-d",
            db,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            f"/backups/{dump_name}",
        ]
    )
    print("\n✓ Local database restored from prod dump.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_backup = sub.add_parser("backup", help="Dump the prod (Neon) database into ./backups")
    p_backup.add_argument("--url", help="Source Postgres URL (else BACKUP_SOURCE_URL env)")
    p_backup.set_defaults(func=backup)

    p_restore = sub.add_parser("restore", help="Restore a dump into the local DB container")
    p_restore.add_argument("--backup", help="Dump file to restore (default: latest)")
    p_restore.set_defaults(func=restore)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
