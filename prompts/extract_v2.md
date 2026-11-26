You read one document from NutriNIN's collection and fill in a small record about it.

What NutriNIN does: Helps a hostel mess plan balanced South Indian menus using NIN's Dietary Guidelines for Indians (2024) and the Indian Food Composition Tables.

Rules:
- Reply with one JSON object and nothing else: no explanation, no Markdown fences.
- Use only what the document says. If it does not say, use null for the year and [] for a list.
- Never infer a year from context or the current date; use a year only when that number appears in the document.
- summary: one or two plain sentences, at most 300 characters.
- topics: 1 to 6 short topics.
- Every list holds short values copied from the document, at most 8.

What each field means:
- doc_kind: what kind of document this is.
- year: the year it was published or came into force.
- language: the main language of the text (en, ta, hi or other).
- food_code: every "food code" this document is mainly about.
- food_name: every "food name" this document is mainly about.
- food_group: every "food group" this document is mainly about.
- energy_kcal: every "energy kcal" this document is mainly about.
- protein_g: every "protein g" this document is mainly about.
- iron_mg: every "iron mg" this document is mainly about.
- fibre_g: every "fibre g" this document is mainly about.
- per_100g: every "per 100g" this document is mainly about.
