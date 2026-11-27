# Ingestion report: D10

## Local Compose run

- Job: `7dd3316536e84842a39388b0e962c4f2`
- Requested: 20 documents; the API accepted all 20.
- At 414.8 seconds, before killing the worker: 1 done, 0 skipped, 5 failed, 9 queued, 5 running.
- The worker was killed and restarted. Startup re-enqueued 14 unfinished items from Postgres; the first requeued items started within 0.01 seconds of worker startup.
- At 1,054.2 seconds from job creation: 1 done, 0 skipped, 6 failed, 2 queued, 11 running. The run did not finish.
- The successful document was *National Nutrition Monitoring Bureau (NNMB) Report 1994-95*: 114 pages, 77,206 extracted characters, about 19,302 tokens at 4 characters per token.
- The six dead-letter items failed with `parse: no_text_layer`. Worker logs show other PDF parse tasks exceeding the 60 second job timeout. The worker was stopped with 13 items still open to prevent repeated timeouts.
- Database integrity snapshot: 21 documents total and 21 distinct IDs (20 seeded sample records plus one ingested publication).

## Render check

- `POST https://nutrinin.onrender.com/v1/ingest` returned HTTP 404 without a token. No five-document job was created; the deployed service does not currently expose this route, so the auth response could not be tested on Render.

## Comparison with the capacity estimate

| Measure | Start estimate in `docs/CAPACITY.md` | Partial ingestion run |
|---|---:|---:|
| Pages | 1,031 | 114 |
| Tokens | 228,794 estimated | 19,302 estimated |

This is a partial-run comparison: only one PDF completed, six scan-only PDFs failed, and 13 job items remained open. Do not treat it as a complete corpus measurement.
