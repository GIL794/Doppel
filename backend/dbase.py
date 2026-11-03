"""Database layer: SQLite by default, PostgreSQL when DATABASE_URL is set.

The app talks to one tiny interface (`run`, `ensure_column`, `script`). SQL is
written once in SQLite style with `?` placeholders; for PostgreSQL the layer
translates placeholders and the few DDL differences. Nothing here changes
behaviour for the default SQLite build.
"""
import sqlite3
import threading
import time

_PG_PING_AFTER = 30.0  # seconds idle before a connection is health-checked


class Database:
    def __init__(self, sqlite_path=None, url=None):
        self.lock = threading.Lock()
        self.url = url or ""
        self.postgres = bool(self.url)
        self._last_use = time.monotonic()
        if self.postgres:
            self._connect_pg()
        else:
            self.conn = sqlite3.connect(sqlite_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row

    # -- postgres plumbing
    def _connect_pg(self):
        import psycopg
        from psycopg.rows import dict_row
        self.conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row,
                                    connect_timeout=15)

    def _ensure_alive(self):
        if not self.postgres:
            return
        if time.monotonic() - self._last_use > _PG_PING_AFTER or self.conn.closed:
            try:
                if self.conn.closed:
                    raise RuntimeError("closed")
                self.conn.execute("SELECT 1")
            except Exception:
                try:
                    self.conn.close()
                except Exception:
                    pass
                self._connect_pg()  # a ping is safe to redo; statements are never retried
        self._last_use = time.monotonic()

    @staticmethod
    def _pg_sql(sql):
        return sql.replace("%", "%%").replace("?", "%s")

    @staticmethod
    def _pg_ddl(sql):
        return (sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
                   .replace(" REAL ", " DOUBLE PRECISION ")
                   .replace(" REAL,", " DOUBLE PRECISION,"))

    # -- public interface
    def run(self, sql, args=(), commit=False):
        """Run one statement. Returns (rows, rowcount); rows is [] for statements
        that return nothing. SQLite commits only when asked; PostgreSQL runs in
        autocommit so every statement is its own transaction."""
        with self.lock:
            if self.postgres:
                self._ensure_alive()
                cur = self.conn.execute(self._pg_sql(sql), args)
                rows = cur.fetchall() if cur.description else []
                return rows, cur.rowcount
            cur = self.conn.execute(sql, args)
            if commit:
                self.conn.commit()
            return cur.fetchall(), cur.rowcount

    def script(self, ddl):
        with self.lock:
            if self.postgres:
                self._ensure_alive()
                for stmt in self._pg_ddl(ddl).split(";"):
                    if stmt.strip():
                        self.conn.execute(stmt)
            else:
                self.conn.executescript(ddl)
                self.conn.commit()

    def ensure_column(self, table, name, ddl):
        with self.lock:
            if self.postgres:
                self._ensure_alive()
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {self._pg_ddl(ddl)}")
                return
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                self.conn.commit()
            except Exception:
                pass  # column already exists

    def close(self):
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                pass
