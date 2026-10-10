# Persistent control plane on a free web service

The desktop's default API address stays `https://serpent-studio.onrender.com`.
The web service can use an independently provisioned PostgreSQL database without
a paid Render disk. This code does not create a database account or provision any
cloud resource. A provider's free quota, retention and availability still apply.

Install the server-only dependency with `python -m pip install -r server/requirements.txt`.
It is not a desktop dependency. Configure these values privately in the service's
environment settings, never in Git, release assets, command output or screenshots:

- `SERPENT_DATABASE_URL`: the PostgreSQL provider's connection URL.
- `SERPENT_ADMIN_USER`: the existing bootstrap administrator's username.
- `SERPENT_ADMIN_PASS`: a new, unique password of at least 12 characters. Rotate
  the previously published password; deleting it from current source is not a rotation.

Start with `python server/control_plane.py`. `PORT` is supplied by Render.
PostgreSQL is selected only when `SERPENT_DATABASE_URL` is configured. Connection
errors fail closed; there is no silent fallback to ephemeral SQLite. Without a
PostgreSQL URL, Render still requires an actual persistent disk mount for SQLite.
SQLite without extra dependencies remains available for local development.

Remote PostgreSQL uses TLS with hostname/certificate verification (`verify-full`),
using system CAs unless the URL specifies a custom CA file. Common provider URLs
with `sslmode=require` are upgraded to verified TLS. Disabling TLS is accepted only
for loopback development connections. Connection and SQL timeouts are bounded.
HTTP bodies are limited to 2 MiB, client sockets to 15 seconds, and concurrent
request workers to 32 (overload receives 503). Each listening server owns its own
database binding. Credentials and connection-error details are not logged. The binary driver package
includes its client libraries; see the [Psycopg installation documentation](https://www.psycopg.org/psycopg3/docs/basic/install.html)
and [PostgreSQL TLS documentation](https://www.postgresql.org/docs/current/libpq-ssl.html).

## Migrate before redeploying an existing SQLite service

Do not redeploy an existing ephemeral SQLite service until an authorized, current
snapshot has been obtained and verified. A developer's local DB copy is not evidence
of the live service's current users. If the provider offers no authorized way to
retrieve the live data, stop and resolve that access first; do not assume the old
database can be recovered after a restart.

The migration utility is deliberately separate from service startup:

```bash
python -m server.migrate export-sqlite --source /absolute/path/control_plane.db --output /private/path/snapshot.json
python -m server.migrate import --input /private/path/snapshot.json
```

Export opens the SQLite source read-only and publishes a new atomic `0600` snapshot;
it refuses to overwrite an existing destination. Add `--include-telemetry` only if
private scripts/error reports should also migrate. Snapshots contain password hashes
and must be treated as secrets. Active sessions are always excluded.

The second command validates the snapshot without connecting to or changing a
destination. After configuring `SERPENT_DATABASE_URL` privately, explicitly adding
`--apply` imports into a completely empty target in one transaction. It refuses a
populated destination and rolls back all imported rows if any constraint fails.
The destination must be dedicated to this control plane, and the web service must
remain stopped until import finishes. Do not start the service first: normal startup
creates an administrator, which correctly makes the destination nonempty.

After import, start the service with the new administrator secret. Password hashes,
roles, restrictions and optional telemetry are retained; all clients must sign in
again. New administrator environment credentials invalidate old administrator
sessions. Restarting with an unchanged environment secret does not undo a password
changed through the authenticated self-service endpoint.

## Isolated regression tests

```bash
python -B -m unittest tests.test_server_storage -v
```

Without a test database, the PostgreSQL integration tests explicitly skip. To run
them, install the server requirements in an isolated test environment and set
`SERPENT_TEST_POSTGRES_URL` privately to a disposable loopback PostgreSQL instance
with both username and initial database named `serpent_test`. Never supply a real
deployment URL. Each test creates and drops only its own uniquely named database;
the test role therefore needs database-creation permission. The test container
should have temporary storage and no production bind mounts.

Coverage includes actual PostgreSQL schema/constraints, transactions, concurrent
password rotation, persistence across server objects, migration rollback/sequences,
HTTP authentication/telemetry and the 2 MiB request-body limit.
