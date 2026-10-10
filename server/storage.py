"""Small DB-API bridge for local SQLite and optional persistent PostgreSQL.

Only application-owned SQL is translated; values always remain bound parameters.
The optional PostgreSQL dependency is intentionally separate from desktop installs.
"""

from __future__ import annotations

from contextlib import contextmanager
import re
import sqlite3
from urllib.parse import urlparse


_SQL_QUOTED = re.compile(r"('(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|--[^\n]*|/\*.*?\*/)", re.DOTALL)


def postgres_sql(sql: str) -> str:
    """Translate qmark placeholders without altering quoted SQL or comments."""
    return ''.join(part if index % 2 else part.replace('?', '%s')
                   for index, part in enumerate(_SQL_QUOTED.split(sql)))


def validate_database_url(url: str) -> None:
    """Validate without returning or including a secret connection URL in errors."""
    try:
        parsed = urlparse(url)
        valid = (parsed.scheme in ('postgres', 'postgresql') and parsed.hostname
                 and parsed.path not in ('', '/') and not parsed.fragment)
        _ = parsed.port
    except (TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('SERPENT_DATABASE_URL must be a PostgreSQL connection URL with a database name.')


class Cursor:
    def __init__(self, raw, postgres: bool):
        self.raw = raw
        self.postgres = postgres

    def execute(self, sql: str, parameters=()):
        self.raw.execute(postgres_sql(sql) if self.postgres else sql, parameters)
        return self

    def fetchone(self):
        return self.raw.fetchone()

    def fetchall(self):
        return self.raw.fetchall()

    @property
    def rowcount(self):
        return self.raw.rowcount

    @property
    def lastrowid(self):
        return self.raw.lastrowid


class Connection:
    def __init__(self, raw, postgres: bool):
        self.raw = raw
        self.postgres = postgres

    def cursor(self):
        return Cursor(self.raw.cursor(), self.postgres)

    def execute(self, sql: str, parameters=()):
        return self.cursor().execute(sql, parameters)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()


class Backend:
    def __init__(self, path: str, database_url: str = ''):
        self.path = path
        self.postgres = bool(database_url)
        self._database_url = database_url
        self._driver = None
        self.integrity_error = sqlite3.IntegrityError
        if self.postgres:
            validate_database_url(database_url)
            try:
                import psycopg
            except ImportError:
                raise RuntimeError('PostgreSQL support requires server/requirements.txt.') from None
            self._driver = psycopg
            self.integrity_error = psycopg.IntegrityError

    def _connect(self):
        if not self.postgres:
            connection = sqlite3.connect(self.path, timeout=10.0, check_same_thread=False)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys = ON')
            return connection
        try:
            from psycopg.conninfo import conninfo_to_dict
            from psycopg.rows import dict_row
            options = conninfo_to_dict(self._database_url)
            host = options.get('host', '')
            loopback = ('localhost', '127.0.0.1', '::1')
            if host not in loopback or options.get('hostaddr', host) not in loopback:
                if options.get('sslmode', 'verify-full') not in ('require', 'verify-ca', 'verify-full'):
                    raise ValueError('Remote PostgreSQL requires authenticated TLS.')
                # Upgrade common provider URLs using sslmode=require to hostname
                # verification instead of relying on encryption alone.
                options['sslmode'] = 'verify-full'
                options.setdefault('sslrootcert', 'system')
                options['gssencmode'] = 'disable'
            options.update(connect_timeout=10, application_name='serpent-control-plane',
                           options='-c statement_timeout=10000 -c lock_timeout=5000')
            return self._driver.connect(**options, row_factory=dict_row, prepare_threshold=None)
        except Exception as exc:
            # Driver errors can contain a DSN/credential. Never propagate their text.
            raise RuntimeError('PostgreSQL connection unavailable (' + type(exc).__name__ + ').') from None

    @contextmanager
    def connection(self):
        raw = self._connect()
        try:
            yield Connection(raw, self.postgres)
            raw.commit()
        except BaseException:
            raw.rollback()
            raise
        finally:
            raw.close()
