"""When DATABASE_URL points at PostgreSQL the suite runs against it too (the
SQLite runs delete their file between loads; PostgreSQL needs the equivalent).
Without DATABASE_URL this file does nothing."""
import os

import pytest


@pytest.fixture(autouse=True)
def _fresh_postgres_rows(request):
    url = os.environ.get("DATABASE_URL")
    # test_api.py is one ordered journey (later tests reuse earlier sign-ups),
    # so its rows are only reset once per run, not per test.
    if url and request.module.__name__ != "test_api":
        import psycopg
        with psycopg.connect(url, autocommit=True) as c:
            tables = [r[0] for r in c.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'").fetchall()]
            if tables:
                c.execute("TRUNCATE " + ", ".join(tables) + " RESTART IDENTITY CASCADE")
    yield
