# Engineering notes: NutriNIN

## D03 - PostgreSQL

### Migrations (upgrade, downgrade, upgrade)

```text
(nutrinin) D:\NutriNIN>uv run alembic downgrade -1
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 3f07bda3c5dc -> ee1336de8a17, add gin index on metadata

(nutrinin) D:\NutriNIN>uv run alembic current
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
ee1336de8a17

(nutrinin) D:\NutriNIN>uv run alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade ee1336de8a17 -> 3f07bda3c5dc, add gin index on metadata

(nutrinin) D:\NutriNIN>uv run alembic history
3f07bda3c5dc -> a4c9f6d2b103 (head), add indexed food_code column and backfill from metadata
ee1336de8a17 -> 3f07bda3c5dc, add gin index on metadata
<base> -> ee1336de8a17, create documents and pages
```

### The loader is idempotent

```text
run 1: records=20 inserted=20 updated=0 unchanged=0 deleted=0
run 2: records=20 inserted=0 updated=0 unchanged=20 deleted=0
run 3 (after editing one record): records=20 inserted=0 updated=1 unchanged=19 deleted=0
```

### Prune removed records

By default, the loader reports database records missing from the JSON file and
leaves them untouched. Add `--prune` to delete those records (and their pages):

```text
uv run python scripts/load_db.py
uv run python scripts/load_db.py --prune
```

Both modes print `deleted=N`; without `--prune`, this is always zero.

### B-tree index for `food_code`

Migration 3 copies `metadata.food_code` into the nullable `documents.food_code`
column and adds `ix_documents_food_code`. The loader writes new values directly
to that column, and `?food_code=H001` filters use the indexed column.

### Sorting

`GET /v1/documents` accepts `sort=title`, `sort=-published_on`, `sort=food_code`,
`sort=doc_type`, or `sort=id`. A leading minus means descending; unsupported
column names return HTTP 400. Ties are ordered by record ID for stable pages.

### Inspect the connection pool

Start the API in one terminal, then send 50 readiness requests in another:

```text
uv run uvicorn nutrinin.api.main:create_app --factory
uv run python scripts/probe_pool.py
```

The API logs `engine.pool.status()` at startup and after request 50. With the
default pool settings, `Pool size: 5` is the base number of reusable connections
and `max_overflow: 5` allows up to five additional temporary connections. At
startup, `Connections in pool: 0`, `Current Overflow: -5`, and `Checked out: 0`
mean no connections have been opened. After the readiness loop, normally one
connection is idle in the pool: `Connections in pool: 1`, `Current Overflow: -4`,
and `Checked out: 0`. A positive overflow means active connections exceeded the
base pool size; checked-out connections are currently in use.

### EXPLAIN for the typed `food_code` column

```text
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM documents WHERE food_code = 'H001';
```

PostgreSQL may still choose a sequential scan for the current 20-row table because
reading the whole table costs less than using the B-tree. As the table grows, a
selective `food_code` lookup can use `ix_documents_food_code`; always check the
actual plan and keep table statistics current.

### Why did the planner choose a Seq Scan on my table?

The table has only 20 rows, so reading them all is estimated to cost less than looking up the GIN index.
For this small table, the index lookup and heap fetch would add work without saving much time.

### When would it switch to the GIN index?

The planner will prefer the GIN index when the query uses an indexed JSONB operator such as `@>` and the table is large and selective enough for that path to cost less than a sequential scan.
