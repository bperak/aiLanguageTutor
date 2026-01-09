"""
PostgreSQL SQL migration runner.

This project historically relied on `docker-entrypoint-initdb.d/init.sql`, which
only runs on first DB initialization. In production, the Postgres volume is
persistent, so new schema additions must be applied explicitly.

Keep it simple: apply curated SQL migrations from `backend/migrations/versions`
exactly once, tracking applied filenames in `schema_migrations`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

import structlog
from sqlalchemy.ext.asyncio import AsyncEngine

logger = structlog.get_logger()


@dataclass(frozen=True)
class MigrationFile:
    """
    Represents a migration file on disk.

    Args:
        version: Unique migration identifier (we use the filename).
        path: Filesystem path to the migration SQL.
    """

    version: str
    path: Path


def _default_versions_dir() -> Path:
    """
    Resolve the default migrations directory.

    Returns:
        Path: `<repo>/backend/migrations/versions`
    """

    # This file is `backend/app/migrations/postgres_migrator.py`
    backend_dir = Path(__file__).resolve().parents[2]
    return backend_dir / "migrations" / "versions"


def list_sql_migrations(versions_dir: Path | None = None) -> List[MigrationFile]:
    """
    List SQL migrations to apply, in deterministic order.

    Args:
        versions_dir: Directory containing curated `*.sql` migrations.

    Returns:
        List[MigrationFile]: Sorted migration files.
    """

    root = versions_dir or _default_versions_dir()
    if not root.exists():
        return []

    files = sorted(p for p in root.glob("*.sql") if p.is_file())
    return [MigrationFile(version=p.name, path=p) for p in files]


def split_sql_statements(sql: str) -> List[str]:
    """
    Split SQL text into executable statements.

    asyncpg (via SQLAlchemy) rejects multiple commands in a prepared statement.
    We split on semicolons while respecting:
    - single-quoted strings: '...'
    - double-quoted identifiers: "..."
    - dollar-quoted blocks: $$...$$ or $tag$...$tag$

    Args:
        sql: Raw SQL file contents.

    Returns:
        List[str]: Individual statements (without trailing semicolons).
    """

    out: List[str] = []
    buf: List[str] = []

    in_single = False
    in_double = False
    dollar_tag: str | None = None

    i = 0
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        # Enter/exit single quotes (ignore if inside dollar quote)
        if dollar_tag is None and ch == "'" and not in_double:
            # Handle escaped '' inside single-quoted string
            if in_single and nxt == "'":
                buf.append(ch)
                buf.append(nxt)
                i += 2
                continue
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue

        # Enter/exit double quotes (ignore if inside dollar quote)
        if dollar_tag is None and ch == '"' and not in_single:
            in_double = not in_double
            buf.append(ch)
            i += 1
            continue

        # Enter/exit dollar-quoted blocks (only when not in single/double)
        if not in_single and not in_double and ch == "$":
            # Detect $tag$ or $$ at current position
            j = i + 1
            while j < len(sql) and sql[j] != "$":
                j += 1
            if j < len(sql) and sql[j] == "$":
                tag = sql[i : j + 1]  # includes both $
                if dollar_tag is None:
                    dollar_tag = tag
                elif dollar_tag == tag:
                    dollar_tag = None
                buf.append(tag)
                i = j + 1
                continue

        # Split on semicolon only when not inside any quoted context
        if ch == ";" and not in_single and not in_double and dollar_tag is None:
            stmt = "".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)

    return out


async def apply_postgres_sql_migrations(
    *,
    engine: AsyncEngine,
    versions_dir: Path | None = None,
) -> None:
    """
    Apply curated Postgres SQL migrations once.

    This will create a `schema_migrations` table if missing, then apply each SQL
    file not yet recorded. Migration execution uses `exec_driver_sql` to support
    multi-statement scripts (including PL/pgSQL blocks).

    Args:
        engine: SQLAlchemy AsyncEngine connected to PostgreSQL.
        versions_dir: Directory containing `*.sql` migrations.
    """

    migrations = list_sql_migrations(versions_dir)
    if not migrations:
        logger.info("postgres_migrations_none_found")
        return

    async with engine.begin() as conn:
        await conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )

        res = await conn.exec_driver_sql("SELECT version FROM schema_migrations;")
        applied: Set[str] = {row[0] for row in res.fetchall()}

        for mf in migrations:
            if mf.version in applied:
                continue

            sql = mf.path.read_text(encoding="utf-8")
            logger.info("postgres_migration_apply_start", version=mf.version)
            for stmt in split_sql_statements(sql):
                await conn.exec_driver_sql(stmt)
            await conn.exec_driver_sql(
                "INSERT INTO schema_migrations (version) VALUES ($1);",
                (mf.version,),
            )
            logger.info("postgres_migration_apply_done", version=mf.version)


