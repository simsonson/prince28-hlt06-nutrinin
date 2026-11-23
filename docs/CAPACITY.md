# Capacity plan: NutriNIN

Full corpus target: + Nutrient Requirements 2020 report, NIN recipe and public-health booklets (2,000+ pages)

<!-- generated:start -->
## Measured on my start corpus (2026-11-23 15:14 UTC)

| What | Value |
|---|---|
| Files | 10 |
| Size on disk | 63.6 MB |
| Pages (PDF pages + 1 per 3,000 characters of text/HTML) | 1,031 |
| Characters of text | 915,175 |
| Estimated tokens (characters / 4) | 228,794 |
| Tokens per page | 222 |
| PDFs with almost no text (scanned? OCR is Day 7) | 1 |
| Files not measured (zip, xlsx, unreadable) | 1 |

## Estimate for the full corpus (target: 2,000 pages)

| What | How | Value |
|---|---|---|
| Scale factor | target / measured | x 1.9 |
| Tokens | measured tokens x scale | 0.44 M |
| Raw files | measured MB x scale | 123 MB |
| Chunks | tokens / 400 x 1.15 overlap | 1,276 |
| Embedding cost, one time | tokens x 1.15 x $0.15 per 1M | $0.08 = Rs 7 |
| Vector storage | chunks x 768 numbers x 4 bytes | 4 MB |
| Text in Postgres | characters x scale x 1.2 | 2 MB |

Assumptions: 4 characters per token, 400-token chunks, 768-dimension embeddings at $0.15 per 1M tokens, Rs 95 per US dollar.
<!-- generated:end -->

## What I conclude

1. Is embedding cost a problem for this product?
    No: the 2,000-page estimate is about 0.44M tokens and Rs 7 for one embedding pass (assuming $0.15/M tokens).
2. Do the vectors and text fit in my free Postgres?
    Yes by this estimate: vectors (~4 MB) + text (~2 MB) = ~6 MB, under Neon Free's 0.5 GB allowance; confirm the live dashboard quota before loading.
3. Which number above am I least sure about, and how will I measure it better?
    Tokens per page (222) is least certain because IFCT has no measured page count and one PDF is nearly textless; OCR representative pages and count with the chosen tokenizer.
4. What changes if the corpus grows 10 times?
    At 10x, estimate ~4.4M tokens, ~12,760 chunks, ~Rs 70 embedding cost, ~40 MB vectors and ~23 MB text.
    This remains below 0.5 GB on paper; remeasure indexes and database overhead before ingestion.

## Object storage

- Status: pending Cloudflare sign-in and R2 bucket creation.
- Planned prefix: `data/raw/`, preserving the local relative paths as object keys.
- Credentials belong only in `.env` (`R2_ENDPOINT`, `R2_BUCKET`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`).
- Current uploadable files: 10; the measured source documents total 63.6 MB.
