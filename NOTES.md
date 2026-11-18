**feat(db): add documents and pages tables with alembic migrations**

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



**feat(db): add idempotent loader with sha256 fingerprints**

(nutrinin) D:\NutriNIN>uv run python scripts/load_db.py
records=20 inserted=20 updated=0 unchanged=0

(nutrinin) D:\NutriNIN>uv run python scripts/load_db.py
records=20 inserted=0 updated=0 unchanged=20

(nutrinin) D:\NutriNIN>uv run python scripts/load_db.py
records=20 inserted=0 updated=1 unchanged=19
