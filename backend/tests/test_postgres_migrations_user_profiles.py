"""
Regression tests for profile build schema.

These tests focus on preventing production regressions where the application
code queries `user_profiles` but the table hasn't been created in a persistent
Postgres volume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Tuple

import pytest

from app.migrations.postgres_migrator import apply_postgres_sql_migrations, list_sql_migrations


def test_migration_list_includes_user_profiles_table() -> None:
    """
    Expected use: curated migrations must include the user_profiles DDL.
    """

    migrations = list_sql_migrations()
    names = {m.version for m in migrations}
    assert "create_user_profiles_table.sql" in names


def test_migration_list_is_deterministic() -> None:
    """
    Edge case: listing should be stable across runs (important for deploys).
    """

    a = [m.version for m in list_sql_migrations()]
    b = [m.version for m in list_sql_migrations()]
    assert a == b


def test_migration_list_handles_missing_directory(tmp_path: Path) -> None:
    """
    Failure case: no crash if migrations dir is missing.
    """

    missing = tmp_path / "does-not-exist"
    assert list_sql_migrations(missing) == []


class _FakeResult:
    def __init__(self, rows: List[Tuple[Any, ...]]):
        self._rows = rows

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return self._rows


class _FakeConn:
    def __init__(self) -> None:
        self.calls: List[Tuple[str, Any]] = []
        self.applied: set[str] = set()

    async def exec_driver_sql(self, statement: str, parameters: Any = None) -> _FakeResult:  # noqa: ANN401
        self.calls.append((statement, parameters))
        st = statement.strip().lower()
        if st.startswith("select version from schema_migrations"):
            return _FakeResult([(v,) for v in sorted(self.applied)])
        if st.startswith("insert into schema_migrations"):
            if isinstance(parameters, tuple) and parameters:
                self.applied.add(str(parameters[0]))
            return _FakeResult([])
        return _FakeResult([])


class _FakeBegin:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self) -> _FakeConn:
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return False


class _FakeEngine:
    def __init__(self, conn: _FakeConn) -> None:
        self._conn = conn

    def begin(self) -> _FakeBegin:
        return _FakeBegin(self._conn)


@pytest.mark.anyio
async def test_apply_migrations_tracks_applied_versions(tmp_path: Path) -> None:
    """
    Expected use: applying migrations should execute SQL and record versions.
    """

    (tmp_path / "a.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "b.sql").write_text("SELECT 2;", encoding="utf-8")

    conn = _FakeConn()
    engine = _FakeEngine(conn)  # type: ignore[arg-type]
    await apply_postgres_sql_migrations(engine=engine, versions_dir=tmp_path)

    assert "a.sql" in conn.applied
    assert "b.sql" in conn.applied


