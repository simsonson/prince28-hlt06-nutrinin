# Engineering notes: NutriNIN

## D03 · PostgreSQL

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
ee1336de8a17 -> 3f07bda3c5dc (head), add gin index on metadata
<base> -> ee1336de8a17, create documents and pages
```

### The loader is idempotent

```text
run 1: records=20 inserted=20 updated=0 unchanged=0
run 2: records=20 inserted=0 updated=0 unchanged=20
run 3 (after editing one record): records=20 inserted=0 updated=1 unchanged=19
```

### EXPLAIN for ?food_code=VALUE

```text
-- 1) What the planner chooses on its own:
Seq Scan on documents  (cost=0.00..11.00 rows=1 width=36) (actual time=1.308..1.308 rows=0.00 loops=1)
  Filter: (metadata @> '{"food_code": "VALUE"}'::jsonb)
  Rows Removed by Filter: 20
  Buffers: shared read=2 dirtied=2
Planning:
  Buffers: shared hit=143 read=8 dirtied=1
Planning Time: 63.642 ms
Execution Time: 1.336 ms

-- 2) Seq scan switched off, to prove the index can be used:
Bitmap Heap Scan on documents  (cost=12.81..16.82 rows=1 width=36) (actual time=1.689..1.690 rows=0.00 loops=1)
  Recheck Cond: (metadata @> '{"food_code": "VALUE"}'::jsonb)
  Buffers: shared hit=1 read=2
  ->  Bitmap Index Scan on ix_documents_metadata_gin  (cost=0.00..12.81 rows=1 width=0) (actual time=1.665..1.665 rows=0.00 loops=1)
        Index Cond: (metadata @> '{"food_code": "VALUE"}'::jsonb)
        Index Searches: 1
        Buffers: shared hit=1 read=2
Planning:
  Buffers: shared hit=1
Planning Time: 0.084 ms
Execution Time: 1.740 ms
```

Why did the planner choose a Seq Scan on my table? (2 lines, your own words)

When would it switch to the GIN index? (1 line)
