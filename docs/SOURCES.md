# NutriNIN — Source Formats and Usage Terms

NutriNIN uses authoritative Indian nutrition references for information retrieval, dietary recommendations and nutrient calculations.

The application stores normalized food-composition records and source metadata. Model-generated text is not treated as an authoritative source of nutrient values.

## 1. Sources

| Source | Format used by NutriNIN | Use in the product | Citation requirement |
|---|---|---|---|
| ICMR-NIN, *Dietary Guidelines for Indians 2024* | PDF publication with page, figure, table and guideline references | Dietary recommendations, food-group proportions and balanced-plate guidance | Cite publication title, page, figure, table or guideline number |
| ICMR-NIN, *Nutrient Requirements for Indians 2020* | PDF publication with RDA summaries and annexures | Reference nutrient requirements and recommended dietary allowances | Cite publication title, page and relevant annexure or table |
| ICMR-NIN, *Indian Food Composition Tables 2017* (IFCT 2017) | Tabular food-composition publication represented as structured records | Programmatic nutrient lookups and recipe-based calculations | Cite IFCT 2017, table, printed page and food code wherever available |

## 2. Stored Data Formats

- Publications are treated as human-readable documents and cited using printed page numbers or relevant sections.
- Food-composition information is represented as structured records with explicit nutrient units.
- Each food record should retain its food code, food name, food group, nutrient values, units and source metadata.
- Recipe calculations must specify ingredient quantities and distinguish raw weights from cooked weights.
- JSON is used as a data transport and storage format. It does not replace the original publication citation.

## 3. Usage Terms and Attribution

- The Dietary Guidelines for Indians 2024 and Indian Food Composition Tables 2017 are published by ICMR-National Institute of Nutrition.
- Both publications permit personal reproduction with full acknowledgment of the source.
- Their copyright notices restrict electronic storage or reproduction for creating a product without prior written permission from the National Institute of Nutrition, Hyderabad.
- NutriNIN must obtain written permission before importing or storing bulk publication content or food-composition extracts in its application.
- Public accessibility does not imply unrestricted redistribution or commercial reuse rights.
- Every permitted use must retain publication title, edition, year, page, table number and original food code wherever applicable.
- NutriNIN must not imply ICMR-NIN endorsement.
- Permission status must be recorded for each source before automated collection or product ingestion.

## 4. Reference Links

- [Official IFCT 2017 PDF](https://www.nin.res.in/ebooks/IFCT2017.pdf)
- [Official NIN downloads](https://www.nin.res.in/downloads/)

## 5. Source Traceability Requirements

For every imported food-composition record, NutriNIN should preserve:

- Original food code.
- Food name and food group.
- Nutrient name, value and unit.
- Original publication title and edition.
- Source table and printed page.
- Raw or cooked food-state information, where applicable.

This metadata ensures that calculated nutrient values can be traced back to their original sources.

## 6. Inspected Source Documents

The following source files have been obtained and inspected for the initial NutriNIN corpus.

| Source ID | Document | Format | Pages | Inspection result |
|---|---|---|---:|---|
| IFCT2017 | Indian Food Composition Tables 2017 | PDF | 584 | Food tables and copyright notice inspected |
| DGI2024 | Dietary Guidelines for Indians 2024 | PDF | 148 | Dietary guidelines and copyright notice inspected |
| NR2020_BRIEF | Nutrient Requirements for Indians 2020 – Brief Note | PDF | 6 | EAR, RDA and nutrient requirement summary inspected |

### Important extraction notes

- IFCT 2017 contains 528 key foods and 151 food components.
- IFCT 2017 food composition values are for raw foods, except eggs.
- Raw and cooked ingredient weights must not be treated as interchangeable.
- The 2020 brief note is not a substitute for the complete Nutrient Requirements report.
- Both IFCT 2017 and Dietary Guidelines 2024 require prior written NIN permission for electronic storage or reproduction for creating a product.
- Automated bulk extraction and product ingestion remain blocked until the necessary permissions are confirmed.

### Local inspection files

- `IFCT2017.pdf`
- `DGI_2024.pdf`
- `brief_note.pdf`

These are inspection copies, not permission to redistribute or publish the original documents.

**Last reviewed:** 23 November 2026 (IST)

**Project:** NutriNIN — HLT-06
