# Dataset: NutriNIN

Helps a hostel mess plan balanced South Indian menus using NIN's Dietary Guidelines for Indians (2024) and the Indian Food Composition Tables.

- **Start target:** Dietary Guidelines 2024 + IFCT 2017 tables
- **Full target:** + Nutrient Requirements 2020 report, NIN recipe and public-health booklets (2,000+ pages)
- **Collected by:** `scripts/fetch.py` as `examate-student-bot` (https://github.com/simsonson/prince28-hlt06-nutrinin): robots.txt respected, at most 4 requests at once, 0.5 s between requests to one site.

## Where the documents come from

- https://www.nin.res.in/
- https://www.ifct2017.com/

## Terms I follow

Public ICMR-NIN publications. Cite guideline and table numbers.

- Every answer links to the original document.
- No personal data is collected.

<!-- generated:start -->
## Sources (generated 2026-11-23 16:50 UTC by scripts/dataset_report.py)

| Source | Licence / terms | Files | MB | Pages* | How | Fetched | Example URL |
|---|---|---|---|---|---|---|---|
| nin | "ICMR-NIN copyright; written permission required for product storage or reproduction" | 10 | 63.6 | 1,031 | http | 2026-11-23 | https://www.nin.res.in/ebooks/IFCT2017.pdf |

**Total:** 10 files, 63.6 MB, 1,031 pages. Not downloaded: 2 blocked by permission, 0 blocked by robots.txt, 0 failed.
Duplicate content groups: 0; extra URLs with the same bytes: 0.

*Pages = PDF pages, plus one page per 3,000 characters of text or HTML.

## Files (first 10 of 10)

The complete list, with a sha256 fingerprint of every file, is `data/manifest.jsonl`.

| # | Title / file | Source | Pages | Fetched | URL |
|---|---|---|---|---|---|
| 1 | Dietary Guidelines for Indians 2024 | nin | 148 | 2026-11-23 | https://nin.res.in/dietaryguidelines/pdfjs/locale/DGI_2024.pdf |
| 2 | Dietary Guidelines for Indians 2024 (NIN website) | nin | 139 | 2026-11-23 | https://www.nin.res.in/downloads/DietaryGuidelinesforNINwebsite.pdf |
| 3 | Indian Food Composition Tables 2017 | nin |  | 2026-11-23 | https://www.nin.res.in/ebooks/IFCT2017.pdf |
| 4 | National Nutrition Monitoring Bureau (NNMB) Report 2020 | nin | 166 | 2026-11-23 | https://www.nin.res.in/downloads/NNMBReport06Nov20.pdf |
| 5 | National Nutrition Monitoring Bureau (NNMB) Report 1977 | nin | 22 | 2026-11-23 | https://www.nin.res.in/downloads/Report_for_the_year_1977.pdf |
| 6 | National Nutrition Monitoring Bureau (NNMB) Report 1979 | nin | 96 | 2026-11-23 | https://www.nin.res.in/downloads/Report_for_the_year_1979.pdf |
| 7 | National Nutrition Monitoring Bureau (NNMB) Report 1994-95 | nin | 114 | 2026-11-23 | https://www.nin.res.in/downloads/Report_Of_The_NNBB_NCAER94-95.pdf |
| 8 | National Nutrition Monitoring Bureau (NNMB) Report 1975-1980 | nin | 142 | 2026-11-23 | https://www.nin.res.in/downloads/Report_Of_Urban_Population_75-80.pdf |
| 9 | National Nutrition Monitoring Bureau (NNMB) Report 1972-1997 | nin | 90 | 2026-11-23 | https://www.nin.res.in/downloads/Reports-for%20the%2025%20years(1972-97).pdf |
| 10 | Special Report on Elderly & Adolescents Diet & Nutritional Status | nin | 114 | 2026-11-23 | https://www.nin.res.in/downloads/Special_Report_on_Elderly&_Adolescents%20Diet_&_Nutritional_St.pdf |
<!-- generated:end -->

## Known gaps

- The start target is present: DGI 2024 (two copies) and IFCT 2017 are downloaded. IFCT 2017 could not be measured as a PDF (page/text count is blank), so verify extraction or OCR before relying on it.
- The full target is incomplete: 10 files and 1,031 measured pages are collected. The planned Nutrient Requirements 2020 report and recipe/public-health booklets are not represented; 2 registry URLs remain permission-blocked.
- One PDF has almost no extractable text and one file is not measured (likely unsupported or unreadable); inspect these before indexing. The 222 tokens/page estimate is uncertain.
- The downloader checks robots.txt before downloads. No URL was marked robots-blocked, but the manifest does not preserve robots.txt rules; save an audit note next time.
- Two DGI URLs appear to be alternate copies. They are not byte-identical, but compare their extracted content before indexing both.

Parsing coverage: 100% of files (10 parsed / 10 parsed+failed)
Parsing coverage: 100% of pages (1,616 parsed / 1,616 parsed+failed)
