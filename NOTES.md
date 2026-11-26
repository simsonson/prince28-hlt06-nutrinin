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


## D04 Â· Docker, Compose and tests

### The image

```text
docker images nutrinin:dev
                                                                                           i Info â†’   U  In Use
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
nutrinin-api-1       nutrinin-api             "sh -c 'exec uvicornâ€¦"   api       5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
nutrinin-db-1        pgvector/pgvector:pg17   "docker-entrypoint.sâ€¦"   db        5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:5434->5432/tcp, [::]:5434->5432/tcp
nutrinin-migrate-1   nutrinin-migrate         "sh -c 'alembic upgrâ€¦"   migrate   5 minutes ago   Exited (0) 5 minutes ago
nutrinin-redis-1     redis:7-alpine           "docker-entrypoint.sâ€¦"   redis     5 minutes ago   Up 5 minutes (healthy)     0.0.0.0:6379->6379/tcp, [::]:6379->6379/tcp

docker compose logs migrate   (first up, then after down + up)

migrate-1  | INFO  [alembic.runtime.migration] Running upgrade  -> ee1336de8a17, create documents and pages
migrate-1  | INFO  [alembic.runtime.migration] Running upgrade ee1336de8a17 -> 3f07bda3c5dc, add gin index on metadata
migrate-1  | INFO  [alembic.runtime.migration] Running upgrade 3f07bda3c5dc -> a4c9f6d2b103, add indexed food_code column and backfill from metadata
migrate-1  | records=20 inserted=20 updated=0 unchanged=0 deleted=0

```

### Breaking the database on purpose

```text
db stopped:  /health â†’ {"status":"ok","app":"nutrinin","env":"local"}
db stopped:  /ready  â†’ {"status":"not_ready","checks":{"database":false,"records_loaded":false}, "records_count":0}
db started:  /ready  â†’ {"status":"ready","checks":{"database":true,"records_loaded":true},"records_count":20}
```

Why should a load balancer stop sending traffic here but not restart the app?

The load balancer should stop routing to this instance while `/ready` returns 503, since it cannot serve requests without the database or loaded records.
`/health` still returns 200, so the app process is alive; restarting it will not fix a database outage and may cause needless restart loops.

### Tests and coverage

```text
uv run poe test              â†’ 22 passed in 0.61s
uv run poe test-integration  â†’ 7 passed in 4.15s
coverage TOTAL, unit only    â†’

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

coverage TOTAL, with integration tests â†’

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
`store.py` (0%, lines 3â€“39): its JSON load/search/readiness code is never exercised; that matters if this store is intended to serve records.
`logging_setup.py` (54%, missing lines 16â€“28): JSON formatting and logging setup paths are partly untested; this mainly affects structured logs and request-ID diagnostics.
### Production image and Compose restart checks

1. The production image ran successfully against Neon: `/ready` returned `200` with `status: ready`, database `true`, records loaded `true`, and `records_count: 20`.
2. The largest image layer is the 96.2 MB virtual-environment copy, because it contains Python and the runtime dependencies installed by `uv`.
3. The HTML report showed `store.py` fully red; `tests/unit/test_store.py::test_record_store_loads_and_searches_records` turns its load, readiness, search, and lookup lines green (store coverage rose to 84%).
4. With `restart: true` under `api.depends_on.db`, `docker compose restart db` restarted the API after the database became healthy; its container ID stayed the same, but its uptime reset and health returned to starting.


## D05 Â· CI/CD and going live

- **Live URL:** https://nutrinin.onrender.com
- **CI run for CI/CD pull request (#11):** GitHub Actions run #16 â€” https://github.com/simsonson/prince28-hlt06-nutrinin/actions
- **First automatic CD run:** GitHub Actions CD run #11 â€” https://github.com/simsonson/prince28-hlt06-nutrinin/actions
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

### Production approval gate

- A required reviewer is worth the delay for high-risk releases, especially database, security, or data changes where a second look can prevent an expensive production mistake.
- For small, reversible changes with strong CI and a tested rollback, the approval wait can cost more than the added assurance.

### Change lead time (three latest automatic CD runs)

| CD run | Merge time (IST) | â€œSmoke test passedâ€ time (IST) | Change lead time |
|---|---:|---:|---:|
| [#12](https://github.com/simsonson/prince28-hlt06-nutrinin/actions/runs/44768546570) | 9:26:47 PM | 9:28:55 PM | 2m 08s |
| [#15](https://github.com/simsonson/prince28-hlt06-nutrinin/actions/runs/44774748023) | 10:03:08 PM | 10:05:31 PM | 2m 23s |
| [#16](https://github.com/simsonson/prince28-hlt06-nutrinin/actions/runs/44782991370) | 10:52:55 PM | 10:55:18 PM | 2m 23s |

- Times are IST; smoke-test times use the successful GitHub Actions step completion time, which follows the script's `Smoke test passed` output.
- **Average change lead time:** 2m 18s.
- **Slowest CD step:** Smoke test production, about 32 seconds in each run.

### Rollback drill

- **Rollback SHA:** d01697cc692ce92f9495148cdd93c4cddc4063eb
- **Rollback started:** 2026-11-20 09:37 IST
- **Rollback smoke test:** PASS
- **Roll-forward SHA:** efc4b0d81c7159750366bfa6da2b9a3959cfabe1
- **Roll-forward duration:** 4 minutes 35 seconds

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
- **Fix:** Updated the health route to support both GET and HEAD. Local verification returned HTTP 200 for both methods, and the deployed monitor badge was subsequently verified Up.
- **Final verification:** 2026-11-22 01:36 IST. The public UptimeRobot status badge for monitor `804746196` returned HTTP 200 with `aria-label="status: up"`. The monitor is currently Up.
- **One thing that would make my live app faster on its first request:** Avoid Render cold starts by using an always-on service configuration rather than allowing the service to spin down.

### Final deployment evidence

- **Verified at:** 2026-11-22 01:36 IST.
- **Live version:** `0e1fe85bae36cc114edf08f2052e9b1b64b778b3` (current `origin/main`).
- **GET `/health`:** HTTP 200; `status=ok`, `env=production`.
- **GET `/ready`:** HTTP 200; database check passed and 20 records were loaded.
- **UptimeRobot:** HTTP 200 public badge response; monitor state `up`.
- **Rollback/roll-forward drill:** The recorded drill rolled back to `d01697cc692ce92f9495148cdd93c4cddc4063eb`, passed its smoke test, and rolled forward to `efc4b0d81c7159750366bfa6da2b9a3959cfabe1` in 4m 35s. The CD workflow skips migrations for rollback and verifies the exact image before deployment.
- **Practice test:** `uv run pytest -q` completed with **24 passed**, 7 integration tests skipped, and no failures. This exceeds the target score of 16.

### Human approval gate

- Production approval is worth the delay for database migrations, security-sensitive changes, and high-impact releases where human verification reduces deployment risk.
- For routine, low-risk bug fixes and documentation updates, automated tests and deployment are usually sufficient to avoid unnecessary delays.


## D06 Â· Collecting the corpus

- Start target: Dietary Guidelines 2024 + IFCT 2017 tables
- Collected today: 10 files, 1,031 measured pages, 63.6 MB (from DATASET.md)
- Doors used: URL list

### Licence check

| Source | Licence or terms, in my words | May I show full text in answers? |
|---|---|---|
| ICMR-NIN | Publicly accessible; registry records written permission as required for product storage or reproduction | Do not show full text unless permission explicitly covers that use |

### robots.txt

- Site: `www.nin.res.in` (also `nin.res.in`). The downloader fetches `/robots.txt` and applies its rules before requesting source URLs; exact directives were not saved in the manifest, so I cannot quote them reliably from this run.
- No downloaded URL was marked blocked by robots.txt; 2 latest manifest entries remain permission-blocked. The collector did not bypass restrictions.

### Kill and resume

- Run 1: Ctrl+C point is not recorded in the manifest/log available in the repo.
- Run 2: 10 files are currently downloaded; the original run counters were not retained, so they cannot be reconstructed exactly.
- Run 3: downloaded=0, skipped=10 on a rerun with the same completed URLs (expected resume behavior; confirm from console output if retained).

### Capacity (from docs/CAPACITY.md)

- Tokens per page, measured: 222 estimated tokens/page (characters Ã· 4; low confidence because IFCT has no extracted page count and one PDF is nearly textless)
- Full corpus: 0.44 M tokens, 1,276 chunks, embedding about Rs 7, vectors 4 MB
- The number that surprised me most, and why: only 222 estimated tokens/page; extraction gaps make this a likely underestimate, so OCR and a real tokenizer may change it substantially.

### One thing that went wrong today, and how I fixed it

The report initially showed an empty corpus because its generated sections were stale. Reran `scripts/dataset_report.py` against the current manifest; it measured 10 downloaded files and exposed one unmeasured file plus a likely scanned PDF.

### Stretch metrics from `data/manifest.jsonl`

- Per source: `nin` — 10 downloaded files, 63.6 MB; 2 latest source entries are permission-blocked.
- Slowest site: not available; per-request timing is not retained in the manifest.
- Retries: 0 downloaded files needed more than one attempt; duplicate content groups: 0, with 0 extra URLs sharing bytes.
- Object storage: 10 `data/raw/` objects uploaded to Supabase bucket `nutrinin-raw`, totaling 63,625,537 bytes; each key was verified with `head_object`.


## D06 ¯ Object storage
- Object Storage:
Supabase Storage (S3-compatible API)

- Bucket:
nutrinin-raw

- Upload method:
AWS CLI (S3 sync)

- Access:
Private bucket using server-side credentials

- Purpose:
Store raw NIN/ICMR PDFs for NutriNIN ingestion workers.

### D07 · Parsing my corpus

## Parser comparison

<!-- parsers:start -->
| File | Parsers (A / B) | Pages | A found | B found | Time (A / B) | Better, why |
|---|---|---|---|---|---|---|
| dgi-2024-1861f1dd.pdf | PyMuPDF / pypdf | 148 | 363,093 chars, 1057 headings, 57 tables | 314,369 chars, 1 headings, 0 tables | 35.13 s / 20.00 s | PyMuPDF: more text, headings, and 57 tables |
| ifct2017-5c74e0d0.pdf | PyMuPDF / pypdf | 585 | 1,375,884 chars, 16328 headings, 226 tables | FAILED: corrupt | 39.66 s / 0.08 s | PyMuPDF parsed it; pypdf failed |
| reports-for-the-25-years-1972-97-79272799.pdf | PyMuPDF / pypdf | 90 | 48,366 chars, 62 headings, 35 tables | 43,085 chars, 0 headings, 0 tables | 9.40 s / 0.25 s | PyMuPDF: more text and 35 tables |
| special-report-on-elderly-adolescents-diet-nutri | PyMuPDF / pypdf | 114 | 166,587 chars, 130 headings, 99 tables | 106,244 chars, 1 headings, 0 tables | 27.13 s / 1.80 s | PyMuPDF: more text, headings, and 99 tables |
| dietaryguidelinesforninwebsite-e40419ab.pdf | PyMuPDF / pypdf | 139 | 214,454 chars, 109 headings, 43 tables | 201,798 chars, 14 headings, 0 tables | 15.23 s / 5.40 s | PyMuPDF: more text, headings, and 43 tables |
| nnmbreport06nov20-3dd70499.pdf | PyMuPDF / pypdf | 166 | 371,259 chars, 714 headings, 196 tables | 255,917 chars, 0 headings, 0 tables | 87.71 s / 9.96 s | PyMuPDF: more text, headings, and 196 tables |
| report-for-the-year-1979-be37a2b0.pdf | PyMuPDF / pypdf | 96 | 136,465 chars, 14 headings, 90 tables | 68,960 chars, 0 headings, 0 tables | 24.02 s / 2.21 s | PyMuPDF: more text, headings, and 90 tables |
| report-of-the-nnbb-ncaer94-95-5a21bdac.pdf | PyMuPDF / pypdf | 114 | 76,969 chars, 54 headings, 29 tables | FAILED: corrupt | 5.75 s / 0.07 s | PyMuPDF parsed it; pypdf failed |
| report-of-urban-population-75-80-e1dc6dc5.pdf | PyMuPDF / pypdf | 142 | 169,131 chars, 20 headings, 161 tables | 93,022 chars, 0 headings, 0 tables | 18.61 s / 1.32 s | PyMuPDF: more text, headings, and 161 tables |
| report-for-the-year-1977-89248589.pdf | PyMuPDF / pypdf | 22 | 17,092 chars, 7 headings, 6 tables | 13,942 chars, 0 headings, 0 tables | 0.85 s / 0.07 s | PyMuPDF: more text, headings, and 6 tables |
<!-- parsers:end -->

### Parsing stats

- Files in the manifest: 10 · parsed: 10 · failed: 0 · pages in Postgres: 1,616
- Parsing coverage: 100% of files (10/10 manifest files; counted by matching manifest SHA-256 values to Postgres)

### Failures by reason

| Reason | Files | What I did |
|---|---|---|
| No current corpus parse failures | 0 | No action needed; all 10 manifest files are present in Postgres |

- The comparison exposed a parser-specific failure: `ifct2017-5c74e0d0.pdf`, reason `corrupt` in pypdf; I used PyMuPDF, which parsed all 585 pages and detected 226 tables. The other pypdf failure was `report-of-the-nnbb-ncaer94-95-5a21bdac.pdf`, also parsed by PyMuPDF.

### What I saw when I read my parsed pages

- A page where the heading path is right (document, page, path): *Dietary Guidelines*, p. 22, `DIETARY GUIDELINES → Eat variety of foods to ensure a balanced diet → enable them to be fit and active` (page text begins with Guideline 1).
- Something that came out wrong (document, page, what): *National Nutrition Monitoring Bureau*, p. 39, a wide table became generic `Col1`–`Col15` columns with mostly empty cells, so the column labels and layout were not preserved usefully.
- A table: Markdown grid or loose text? (document, page): Markdown grid, *Dietary Guidelines*, p. 15 (`|Particulars|Col2|...` and separator rows); some headers are still generic.

### My parser choice

- For PDFs I use **PyMuPDF** because on the 10-file comparison it detected tables on all 10 (6–226 per file), while pypdf detected 0 on its 8 successful files and failed on 2. For the Dietary Guidelines 2024 PDF, PyMuPDF found 363,093 chars and 1,057 headings versus pypdf's 314,369 chars and 1 heading; it was slower (35.13 s vs 20.00 s), but the structure is much more useful.
- A kind of document in my corpus that neither parser handles well: very wide, dense tabular reports such as IFCT 2017; PyMuPDF detects tables, but the page comparison shows extracted cell structure can still be incomplete or generic. OCR would also be needed for any scanned pages without a text layer.

### One thing that went wrong today, and how I fixed it

`uv run` first failed because the default uv cache under the user profile was inaccessible (`Access is denied`). I reran with `UV_CACHE_DIR=D:\NutriNIN\.uv-cache`, inside the workspace; the comparison completed and updated this section.


### D08 · LLM gateway

- Primary: gemini-3.8-flash (Gemini) · fallback: openai/gpt-oss-20b (Groq)
- First question on my laptop: first words after ___ s, total ___ s, tokens in ___ / out ___, cost Rs ___
- Same question on my live URL (second, awake request): first words after ___ s. Day 1 target: under 1.5 s

### Tokens: English against Tamil

| Message | tokens in |
|---|---|
| "Hi" (baseline: mostly my system prompt) | |
| The English sentence | |
| The same sentence in Tamil | |

- The Tamil message needs about ___ times the tokens of the English one.

### What the model does without my documents

- Question 6 ("What will vegetable prices be at Koyambedu market tomorrow?"): did it admit it can't know? Its exact words:
- A detail it got wrong or invented (question → what it said → what is true):
- The off-topic question: did it decline in one sentence?

### Fallback and circuit breaker

- With the primary broken: provider ________ , fallback ____ , first words after ___ s
- The question at which "llm call gemini … error" stopped appearing in the log: number ___

### The bill

- /v1/usage today: calls ___ , errors ___ , fallbacks ___ , cost Rs ___
- Average per answered question: Rs ___ (my Day 1 target: under Rs 0.50)

### One thing that went wrong today, and how I fixed it
