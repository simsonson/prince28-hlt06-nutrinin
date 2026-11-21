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

- These references are publicly accessible ICMR-NIN publications and food-composition resources.
- NutriNIN uses the references for research, information retrieval, attribution and nutritional calculation support.
- Publisher attribution, publication titles, editions, publication years, page references, table numbers and food codes must be retained when transforming source information.
- NutriNIN must not be represented as an ICMR-NIN product or imply institutional endorsement.
- Public availability does not automatically grant unrestricted redistribution rights. Before redistributing complete publications or bulk extracts, verify the publisher's current copyright and reuse conditions.
- Derived nutrient values should be published with their source citations, ingredient quantities, calculation inputs and units.

## 4. Reference Links

- [ICMR-NIN official website](https://www.nin.res.in/)
- [Indian Food Composition Tables 2017 reference site](https://www.ifct2017.com/)

## 5. Source Traceability Requirements

For every imported food-composition record, NutriNIN should preserve:

- Original food code.
- Food name and food group.
- Nutrient name, value and unit.
- Original publication title and edition.
- Source table and printed page.
- Raw or cooked food-state information, where applicable.

This metadata ensures that calculated nutrient values can be traced back to their original sources.

**Last reviewed:** 22 November 2026 (IST)

**Project:** NutriNIN — HLT-06
