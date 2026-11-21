# Real User Questions — NutriNIN

## 1. Target User

**Primary user:** Mess supervisor at an engineering college hostel in Chennai.

**Operational context:**
- Serves approximately 600 students.
- Works with a fixed daily food budget per student.
- Plans South Indian meals such as rice, sambar, idli, pongal, kootu and vegetable curries.
- Needs reliable nutritional information to prepare balanced, affordable menus.

These questions represent realistic queries that the target user may ask while planning hostel meals.

## 2. Evaluation Question Set

The following 10 questions form NutriNIN's initial evaluation dataset for Week 3.

| # | User Question | Type | Expected Source / Answer Location | Multi-page? |
|---|---|---|---|---|
| 1 | What does the NIN 'My Plate for the Day' recommend for vegetables and fruits? | Simple retrieval | Dietary Guidelines for Indians 2024, Figure 1.3, page 6; Guideline 6, page 49 | No |
| 2 | How much protein per day do the 2020 nutrient requirements give for an adult man with moderate activity? | Simple retrieval | ICMR-NIN Nutrient Requirements for Indians 2020, RDA Summary, Annexure IA, PDF page 3 | No |
| 3 | What is the iron content of ragi per 100 g according to IFCT 2017? | Simple retrieval | Indian Food Composition Tables 2017, Table 5: Minerals and Trace Elements, printed page 153, food row A010 | No |
| 4 | Our hostel lunch is rice, sambar, potato fry, curd and pickle every day. Evaluate this meal against NIN guidelines and suggest three affordable improvements for 600 students. | Multi-step reasoning | Dietary Guidelines for Indians 2024, Figure 1.3 and Table 1.2a, pages 6–7; Guidelines 6 and 7, pages 47–56; relevant IFCT 2017 nutrient tables for rice, pulses and vegetables | Yes |
| 5 | Compare the protein and dietary fibre content of one serving of idli-sambar and poori-masala. | Comparison and calculation | IFCT 2017, Table 1: Proximate Principles and Dietary Fibre, pages 41–43; ingredient records for rice, urad dal, wheat flour, potato and vegetables. Recipe quantities must be defined before calculation. | Yes |
| 6 | What will vegetable prices be at Koyambedu market tomorrow? | Unanswerable / Out of scope | No supporting information in the NIN or IFCT knowledge base. The system must respond: "I don't know." | No |
| 7 | We serve rice and sambar regularly. How much pulses should we include in a balanced daily menu for each student according to NIN? | Simple retrieval | Dietary Guidelines for Indians 2024, Figure 1.3 and Table 1.2a, pages 6–7 | No |
| 8 | Can I replace some of the regular rice with ragi, bajra or other millets without affecting the nutritional balance? | Multi-step reasoning | Dietary Guidelines for Indians 2024, Guideline 1, pages 5–7; millet recommendations, page 23; IFCT 2017, Table 1: Proximate Principles and Dietary Fibre, relevant cereal and millet records | Yes |
| 9 | How much vegetables and fruits should I provide to each student daily, and can potato be counted towards the vegetable target? | Simple retrieval and interpretation | Dietary Guidelines for Indians 2024, Guideline 6, page 49; Figure 1.3, page 6 | Yes |
| 10 | Our mess uses a lot of cooking oil and salt. What does NIN recommend to reduce them while keeping our South Indian meals nutritious and tasty? | Multi-step reasoning | Dietary Guidelines for Indians 2024, Guideline 7, pages 51–56; Guideline 11, pages 73–76; Guideline 13, pages 81–88 | Yes |

## 3. Evaluation Objectives

The 10 questions evaluate the following capabilities:

1. **Direct factual retrieval:** Questions 1–3 test whether the system can retrieve information from trusted ICMR-NIN publications and IFCT 2017.
2. **Multi-step reasoning:** Questions 4 and 8 test whether the system can combine dietary recommendations with food composition information.
3. **Numerical comparison:** Question 5 tests recipe-based nutrient calculations and comparison between two meals.
4. **Hallucination prevention:** Question 6 tests whether the system recognizes information that is unavailable in its knowledge base.
5. **Practical menu planning:** Questions 7–10 test whether the system can provide useful dietary guidance for hostel mess operations.

## 4. Expected System Behaviour

NutriNIN must follow these rules when answering the evaluation questions:

1. **Trusted nutrient data:** Nutrient values must be retrieved from official IFCT 2017 records and calculated programmatically. The language model must not invent nutrient values.
2. **Evidence-based recommendations:** Dietary recommendations must be supported by ICMR-NIN publications.
3. **Source citations:** Every factual answer must include the source document and the relevant page, figure, table or section.
4. **Transparent calculations:** Recipe calculations must use explicitly defined ingredient quantities and distinguish raw weights from cooked weights.
5. **Honest uncertainty:** If the requested information is unavailable in the knowledge base, the system must respond with "I don't know" rather than generate an unsupported answer.
6. **Practical recommendations:** Menu suggestions should consider the hostel's operational context, including 600 students and a fixed food budget.
7. **Traceability:** Numerical answers should be reproducible using the underlying food composition records and recipe quantities.

## 5. Target Evaluation Criteria

| Evaluation Metric | Target |
|---|---|
| Realistic evaluation questions | 10 |
| Invented nutrient values | 0 |
| Unsupported dietary recommendations | 0 |
| Correct source citations | Required for every factual answer |
| Recipe calculation accuracy | Within 5% of manual calculations |
| Recipe calculation test dataset | 30 recipes |
| Unanswerable question handling | Question 6 must return "I don't know" |

## 6. Scope and Limitations

- The initial knowledge base consists of ICMR-NIN publications and Indian Food Composition Tables.
- The system does not have live market-price information unless an appropriate external data source is separately integrated.
- Nutrient calculations depend on the accuracy of ingredient quantities, food selection and raw-versus-cooked weight handling.
- Recommendations must not be presented as exact nutritional calculations unless the required data and calculation method are available.

## 7. Evaluation Success Definition

NutriNIN will meet its initial evaluation target when:

- All 10 questions can be submitted and evaluated.
- Nutrient values are traceable to official IFCT 2017 records.
- Dietary recommendations are supported by ICMR-NIN sources.
- All factual answers contain appropriate citations.
- Nutrient calculations for 30 test recipes remain within 5% of manual calculations.
- Question 6 correctly produces the response "I don't know."

**Document purpose:** This question set defines the initial real-user evaluation dataset for NutriNIN and will be used to assess retrieval accuracy, nutritional calculations, source grounding and hallucination prevention during Week 3.
