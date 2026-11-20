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


## D04 · Docker, Compose and tests

### The image

```text
docker images nutrinin:dev
                                                                                           i Info →   U  In Use
IMAGE          ID             DISK USAGE   CONTENT SIZE   EXTRA
nutrinin:dev   8258d8250fb4        300MB           70MB


docker run --rm nutrinin:dev id

uid=999(app) gid=999(app) groups=999(app)
```

- Size: 300 MB (target: under 400 MB)
- First build: 15.63 s. After changing one line of code: 12.06 s.
- Which step said CACHED, and why?
- `uv sync --locked --no-install-project --no-dev` was CACHED because app code changed but `pyproject.toml` and `uv.lock` stayed the same.

### The stack

```text
docker compose ps -a

NAME                 IMAGE                    COMMAND                  SERVICE   CREATED         STATUS                     PORTS
nutrinin-api-1       nutrinin-api             "sh -c 'exec uvicorn…"   api       5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
nutrinin-db-1        pgvector/pgvector:pg17   "docker-entrypoint.s…"   db        5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:5434->5432/tcp, [::]:5434->5432/tcp
nutrinin-migrate-1   nutrinin-migrate         "sh -c 'alembic upgr…"   migrate   5 minutes ago   Exited (0) 5 minutes ago
nutrinin-redis-1     redis:7-alpine           "docker-entrypoint.s…"   redis     5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp

docker compose logs migrate   (first up, then after down + up)

migrate-1  | INFO  [alembic.runtime.migration] Running upgrade  -> ee1336de8a17, create documents and pages
migrate-1  | INFO  [alembic.runtime.migration] Running upgrade ee1336de8a17 -> 3f07bda3c5dc, add gin index on metadata
migrate-1  | INFO  [alembic.runtime.migration] Running upgrade 3f07bda3c5dc -> a4c9f6d2b103, add indexed food_code column and backfill from metadata
migrate-1  | records=20 inserted=20 updated=0 unchanged=0 deleted=0

```

### Breaking the database on purpose

```text
db stopped:  /health → {"status":"ok","app":"nutrinin","env":"local"}
db stopped:  /ready  → {"status":"not_ready","checks":{"database":false,"records_loaded":false}, "records_count":0}
db started:  /ready  → {"status":"ready","checks":{"database":true,"records_loaded":true},"records_count":20}
```

Why should a load balancer stop sending traffic here but not restart the app?

The load balancer should stop routing to this instance while `/ready` returns 503, since it cannot serve requests without the database or loaded records.
`/health` still returns 200, so the app process is alive; restarting it will not fix a database outage and may cause needless restart loops.

### Tests and coverage

```text
uv run poe test              → 22 passed in 0.61s
uv run poe test-integration  → 7 passed in 4.15s
coverage TOTAL, unit only    →

=============================================== tests coverage ===============================================
______________________________ coverage: platform win32, python 3.12.13-final-0 ______________________________

Name                             Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------
src\nutrinin\api\deps.py            25      9      0      0    64%   21-22, 26, 31-36
src\nutrinin\api\main.py            40      1      2      1    95%   46
src\nutrinin\api\middleware.py      21      3      0      0    86%   22-24
src\nutrinin\config.py              22      1      0      0    95%   34
src\nutrinin\db\repository.py       48     33     14      0    24%   23, 37-45, 50, 62-83, 86-87, 90, 93-96
src\nutrinin\db\url.py              12      0      4      1    94%   10->12
src\nutrinin\logging_setup.py       22      1      6      1    93%   27
src\nutrinin\store.py               30     30      8      0     0%   3-39
----------------------------------------------------------------------------
TOTAL                              344     78     42      3    73%

9 files skipped due to complete coverage.
22 passed, 7 skipped in 3.59s

coverage TOTAL, with integration tests →

=============================================== tests coverage ===============================================
______________________________ coverage: platform win32, python 3.12.13-final-0 ______________________________

Name                             Stmts   Miss Branch BrPart  Cover   Missing
----------------------------------------------------------------------------
src\nutrinin\api\deps.py            25      2      0      0    92%   35-36
src\nutrinin\api\main.py            40      1      2      1    95%   46
src\nutrinin\api\middleware.py      21      3      0      0    86%   22-24
src\nutrinin\db\repository.py       48      7     14      4    82%   40, 44, 69, 81, 87, 93-96
src\nutrinin\logging_setup.py       22      7      6      0    54%   16-28
src\nutrinin\store.py               30     30      8      0     0%   3-39
----------------------------------------------------------------------------
TOTAL                              344     50     42      5    82%

11 files skipped due to complete coverage.
29 passed in 7.15s

```

Two files or lines my coverage report says are never run, and whether they matter:
`store.py` (0%, lines 3–39): its JSON load/search/readiness code is never exercised; that matters if this store is intended to serve records.
`logging_setup.py` (54%, missing lines 16–28): JSON formatting and logging setup paths are partly untested; this mainly affects structured logs and request-ID diagnostics.
### Production image and Compose restart checks

1. The production image ran successfully against Neon: `/ready` returned `200` with `status: ready`, database `true`, records loaded `true`, and `records_count: 20`.
2. The largest image layer is the 96.2 MB virtual-environment copy, because it contains Python and the runtime dependencies installed by `uv`.
3. The HTML report showed `store.py` fully red; `tests/unit/test_store.py::test_record_store_loads_and_searches_records` turns its load, readiness, search, and lookup lines green (store coverage rose to 84%).
4. With `restart: true` under `api.depends_on.db`, `docker compose restart db` restarted the API after the database became healthy; its container ID stayed the same, but its uptime reset and health returned to starting.


## D05 · CI/CD and going live

- **Live URL:** https://nutrinin.onrender.com
- **CI run for CI/CD pull request (#11):** GitHub Actions run #16 — https://github.com/simsonson/prince28-hlt06-nutrinin/actions
- **First automatic CD run:** GitHub Actions CD run #11 — https://github.com/simsonson/prince28-hlt06-nutrinin/actions
- **CI/CD merge commit:** `a3234e72f93d41c73df471f844f3512bc82449a3`
- **Latest production version previously verified:** `5c588adc65ae280355cd25ec05f3382ddf11e55b`
- **Merge clicked at:**  9:05 PM IST
- **"Smoke test passed" at:** 9:07 PM IST
- **Lead time:** 2 minutes.
- **CD run duration:** 3 minutes 13 seconds.

### Smoke test output from that CD run

```text
ok    /health -> 200, version a3234e72f93d41c73df471f844f3512bc82449a3
ok    /ready -> 200 {'status': 'ready', 'checks': {'database': True, 'records_loaded': True}, 'records_count': 20}
ok    /v1/documents?limit=1 -> 200
Smoke test passed
```

### Rollback drill

- **Rollback SHA:** Not performed yet.
- **Rollback started:** Not recorded.
- **Rollback smoke test:** Not performed.
- **Roll-forward SHA:** Not performed yet.
- **Roll-forward duration:** Not recorded.

**Why can the database stay on the newer schema during rollback?**

The rollback workflow skips migrations, so the database remains at its newer schema. This is safe only if the older application version remains backward-compatible with that schema; this compatibility must be verified before treating the rollback as safe.

### Where my secrets live

- **Neon connection string:** GitHub Secret `DATABASE_URL` and Render environment configuration. Not committed to Git or included in the application image.
- **Render deploy hook:** GitHub Secret `RENDER_DEPLOY_HOOK` only.
- **Live URL variable:** GitHub Actions variable `LIVE_URL` = `https://nutrinin.onrender.com`.

### Monitoring

- **Monitoring service:** UptimeRobot.
- **Monitor ID:** `804746196`.
- **Endpoint:** `https://nutrinin.onrender.com/health`.
- **Check interval:** Every 5 minutes.
- **Alerts:** Email notifications configured.
- **Previous issue:** UptimeRobot received HTTP 405 for HEAD requests because the health route initially supported only GET.
- **Fix:** Updated the health route to support both GET and HEAD. Local verification returned HTTP 200 for both methods. The fix is committed on `fix/health-head-support`; production monitoring must be verified after the fix is merged and deployed.
- **One thing that would make my live app faster on its first request:** Avoid Render cold starts by using an always-on service configuration rather than allowing the service to spin down.
