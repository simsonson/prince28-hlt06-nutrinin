# Ingestion report

<!-- generated:start -->
_Generated 27 Nov 2026 21:45 from the database._

| What | Count |
|---|---|
| Documents in the database | 2 |
| Pages | 136 |
| Tokens of text (characters ÷ 4) | 23,481 |
| Files the parser gave up on | 7 |
| Documents with an extracted record | 2 |
| Documents whose extraction failed | 0 |

| Queue | Count |
|---|---|
| Ingest jobs started | 4 |
| Items finished (done or skipped) | 6 |
| Items that needed more than one try | 30 |
| Items in the dead-letter list | 29 |

Model calls for extraction: 26 · tokens in 33,193 · tokens out 3,453 · cost at list price Rs 1.77

Last job `99e5d82e22c24f719d2298098ce0a92d`: 5 requested, 0 ok, 0 failed, 3.4 minutes.

Dead-letter list by stage: gave up 22, parse 7
<!-- generated:end -->

## What I learnt

- The queue is recoverable because Postgres records item state and the worker re-enqueues unfinished items after startup.
- Scan-only PDFs need OCR before they can be parsed; retries alone leave them in the dead-letter list.
- Queue age is a useful health signal: the oldest queued item grows when workers cannot keep up with incoming work.
