# Real User Questions: NutriNIN

Written the way my user types them.

**User:** Mess supervisor at an engineering college hostel in Chennai feeding 600 students on a fixed daily budget per student.

These 10 questions become my first evaluation set in Week 3. Question 6 is not answerable from my documents: the product must say "I don't know".

| # | Question | Type | Where the answer is (document, page) | More than one page? |
|---|---|---|---|---|
| 1 | What does the NIN 'My Plate for the Day' recommend for vegetables and fruits? | simple | Dietary Guidelines for Indians 2024, Figure 1.3, page 6; Guideline 6, page 49 | No |
| 2 | How much protein per day do the 2020 nutrient requirements give for an adult man of moderate activity? | simple | ICMR-NIN Nutrient Requirements for Indians 2020, RDA Summary, Annexure IA, PDF page 3 | No |
| 3 | What is the iron content of ragi per 100 g in IFCT 2017? | simple | Indian Food Composition Tables 2017, Table 5: Minerals and Trace Elements, printed page 153, row A010 | No |
| 4 | Our hostel lunch is rice, sambar, potato fry, curd and pickle every day. Score it against the NIN guidelines and suggest 3 low-cost changes for 600 students. | multi-step (several pages) | Dietary Guidelines for Indians 2024, Figure 1.3 and Table 1.2a, page 6–7; Guideline 6, pages 47–50; Guideline 7, pages 51–56; IFCT 2017 nutrient tables for rice, pulses and vegetables | Yes |
| 5 | Compare the protein and fibre of idli-sambar and poori-masala breakfasts per serving. | comparison | IFCT 2017, Table 1: Proximate Principles and Dietary Fibre, pages 41–43; relevant ingredient rows for rice, urad dal, wheat flour, potato and vegetables. Use defined recipe quantities to calculate each serving. | Yes |
| 6 | What will vegetable prices be at Koyambedu market tomorrow? | unanswerable: must reply "I don't know" | None: not available in any NIN or IFCT document | - |
| 7 | We serve rice and sambar regularly. How much pulses should we include in a balanced daily menu for each student according to NIN? | simple | Dietary Guidelines for Indians 2024, Figure 1.3 and Table 1.2a, page 6–7 | No |
| 8 | Can I replace some of the regular rice with ragi, bajra or other millets without affecting the nutritional balance? | multi-step | Dietary Guidelines for Indians 2024, Guideline 1, page 5–7; millet recommendations, page 23; IFCT 2017, Table 1: Proximate Principles and Dietary Fibre, relevant cereal and millet rows | Yes |
| 9 | How much vegetables and fruits should I provide to each student daily, and can potato be counted towards the vegetable target? | simple | Dietary Guidelines for Indians 2024, Guideline 6, page 49; Figure 1.3, page 6 | Yes |
| 10 | Our mess uses a lot of cooking oil and salt. What does NIN recommend to reduce them while keeping our South Indian meals nutritious and tasty? | multi-step | Dietary Guidelines for Indians 2024, Guideline 7, pages 51–56; Guideline 11, pages 73–76; Guideline 13, pages 81–88 | Yes |

## Evaluation Notes

- Questions 1–3 test direct factual retrieval from trusted nutrition documents.
- Questions 4, 5 and 8 test multi-step reasoning and numerical calculations using IFCT data.
- Question 6 tests whether the system can recognize missing information and avoid hallucination.
- Questions 7–10 test practical menu-planning knowledge for hostel mess operations.

## Expected Behaviour

1. All nutrient values must come from official IFCT 2017 data and calculations in code.
2. All dietary recommendations must be supported by ICMR-NIN publications.
3. Every answer must include the relevant document, page or table reference.
4. Recipe calculations must use actual ingredient quantities and clearly distinguish raw and cooked weights.
5. When information is unavailable in the knowledge base, the system must respond honestly with "I don't know" instead of generating an unsupported answer.

## Target Evaluation

- 10 realistic user questions.
- Zero invented nutrient values.
- Correct source citations.
- Nutrient calculations within 5% of manual calculations for 30 test recipes.
- Question 6 must return "I don't know".
