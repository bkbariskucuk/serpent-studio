"""Explicit offline SQLite export and empty-target import; never run at startup.

Snapshots contain password hashes and possibly private scripts: keep them private.
Sessions are deliberately excluded so every user must authenticate after migration.
Run ``python -m server.migrate --help``. No command prints connection credentials.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

from .control_plane import Database


TABLE_COLUMNS = {
    'users': ('id', 'username', 'password_hash', 'salt', 'role', 'display_name', 'is_active', 'created_at', 'expires_at', 'restricted_panels'),
    'admin_bootstrap': ('username', 'password_hash', 'salt'),
    'error_reports': ('id', 'username', 'app_version', 'platform', 'exception_type', 'exception_message', 'traceback', 'active_tab', 'recent_logs', 'timestamp'),
    'scripts': ('id', 'username', 'project_name', 'script_content', 'timestamp'),
}


def _publish_private_snapshot(destination: str, snapshot: dict) -> None:
    """Publish a complete 0600 file without overwriting any existing destination."""
    target = Path(destination).absolute()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.serpent-export-', dir=target.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(snapshot, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link publication is atomic and fails if target already exists.
        os.link(temporary, target)
    finally:
        os.unlink(temporary)


def export_sqlite(source: str, destination: str, *, include_telemetry: bool = False) -> dict:
    source_path = Path(source).resolve(strict=True)
    tables = {}
    connection = sqlite3.connect(source_path.as_uri() + '?mode=ro', uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute('BEGIN')  # Consistent read snapshot even with concurrent WAL writes.
        available = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'users' not in available:
            raise ValueError('Source is not a control-plane database.')
        for table, columns in TABLE_COLUMNS.items():
            if table not in available or (table in ('error_reports', 'scripts') and not include_telemetry):
                tables[table] = []
                continue
            rows = []
            for row in connection.execute('SELECT * FROM ' + table):
                value = dict(row)
                if table == 'users':
                    value.setdefault('restricted_panels', '[]')
                    value.setdefault('expires_at', None)
                rows.append({column:value[column] for column in columns})
            tables[table] = rows
    finally:
        connection.rollback()
        connection.close()
    snapshot = {'format':'serpent-control-plane', 'version':1, 'exported_at':time.time(),
                'sessions_included':False, 'tables':tables}
    validate_snapshot(snapshot)
    _publish_private_snapshot(destination, snapshot)
    return {table:len(rows) for table, rows in tables.items()}


def validate_snapshot(snapshot: dict) -> dict:
    if (not isinstance(snapshot, dict) or snapshot.get('format') != 'serpent-control-plane'
            or snapshot.get('version') != 1 or snapshot.get('sessions_included') is not False):
        raise ValueError('Unsupported snapshot format; active sessions cannot be imported.')
    tables = snapshot.get('tables')
    if not isinstance(tables, dict) or set(tables) != set(TABLE_COLUMNS):
        raise ValueError('Snapshot has unexpected tables.')
    for table, columns in TABLE_COLUMNS.items():
        rows = tables[table]
        if not isinstance(rows, list):
            raise ValueError('Snapshot rows must be lists.')
        for row in rows:
            if not isinstance(row, dict) or set(row) != set(columns):
                raise ValueError('Snapshot contains unexpected fields.')
    return {table:len(rows) for table, rows in tables.items()}


def import_snapshot(snapshot: dict, target: Database) -> dict:
    """Import all data in one transaction, refusing any populated destination."""
    counts = validate_snapshot(snapshot)
    with target._lock, target._get_conn() as connection:
        if target._backend.postgres:
            connection.execute('SELECT pg_advisory_xact_lock(73657270656)')
            connection.execute('LOCK TABLE users, sessions, admin_bootstrap, error_reports, scripts IN ACCESS EXCLUSIVE MODE')
        else:
            connection.execute('BEGIN IMMEDIATE')
        for table in (*TABLE_COLUMNS, 'sessions'):
            row = connection.execute('SELECT COUNT(*) AS count FROM ' + table).fetchone()
            if row['count']:
                raise ValueError('Import requires a completely empty destination; no data was overwritten.')
        for table, columns in TABLE_COLUMNS.items():
            placeholders = ','.join('?' for _ in columns)
            sql = 'INSERT INTO ' + table + ' (' + ','.join(columns) + ') VALUES (' + placeholders + ')'
            for row in snapshot['tables'][table]:
                connection.execute(sql, tuple(row[column] for column in columns))
        if target._backend.postgres:
            for table in ('users', 'error_reports', 'scripts'):
                connection.execute("SELECT setval(pg_get_serial_sequence(?, 'id'), COALESCE((SELECT MAX(id) FROM " + table + "), 1), EXISTS(SELECT 1 FROM " + table + "))", (table,))
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    export = commands.add_parser('export-sqlite', help='Read-only source; new private file; sessions excluded')
    export.add_argument('--source', required=True)
    export.add_argument('--output', required=True)
    export.add_argument('--include-telemetry', action='store_true')
    restore = commands.add_parser('import', help='Validate by default; --apply imports into empty PostgreSQL')
    restore.add_argument('--input', required=True)
    restore.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'export-sqlite':
            counts = export_sqlite(args.source, args.output, include_telemetry=args.include_telemetry)
        else:
            with open(args.input, encoding='utf-8') as stream:
                snapshot = json.load(stream)
            counts = validate_snapshot(snapshot)
            if args.apply:
                database_url = os.environ.get('SERPENT_DATABASE_URL', '').strip()
                if not database_url:
                    raise ValueError('Set SERPENT_DATABASE_URL before an explicit import.')
                target = Database(database_url=database_url, bootstrap_admin=False)
                counts = import_snapshot(snapshot, target)
            else:
                print('Validation only; destination was not connected or changed. Use --apply after checking an empty destination.')
        print(json.dumps({'rows':counts, 'sessions_imported':0}))
        return 0
    except Exception as exc:
        # In particular, never print driver messages, DSNs, hashes, or row contents.
        print('Migration did not complete (' + type(exc).__name__ + '). Check configuration and an empty destination.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
