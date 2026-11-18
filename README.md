# NutriNIN

Helps a hostel mess plan balanced South Indian menus using NIN's Dietary Guidelines for Indians (2024) and the Indian Food Composition Tables.

**Status:** Day 1 foundation (FastAPI skeleton, quality gates). Live URL from Day 5.

## Who it's for

Mess supervisor at an engineering college hostel in Chennai feeding 600 students on a fixed daily budget per student.

## The problem

Hostel mess supervisors must prepare balanced meals for hundreds of students while staying within a fixed daily food budget. Although NIN guidelines provide recommended nutrient intake and plate proportions, applying them to everyday South Indian meals like sambar, pongal, kootu, and rice is difficult. Nutrient calculations require knowing the ingredients, quantities, and raw or cooked weights rather than relying on estimates. As a result, planning weekly menus that are nutritious, affordable, and consistent becomes time-consuming and prone to errors. NutriNIN aims to simplify this process by turning food composition data and dietary guidelines into practical menu-planning insights.

## Data sources

NIN Dietary Guidelines for Indians 2024, ICMR-NIN Nutrient Requirements report 2020, IFCT 2017 tables and NIN publications.

- [https://www.nin.res.in/](https://www.nin.res.in/)
- [https://www.ifct2017.com/](https://www.ifct2017.com/)

**Terms:** Public ICMR-NIN publications. Cite guideline and table numbers.

## Hardest problem (my interview story)

Numbers from tables, not from the LLM: nutrients must be computed from IFCT rows multiplied by grams in a recipe (with raw vs cooked weights), in code. Retrieval explains the guideline; the calculator gives every number.

## Signature feature

Weekly menu scorecard: paste a 7-day menu and see protein, iron, fibre and vegetable portions against the NIN plate for each day.

## Target metric

Nutrient numbers within 5% of a hand calculation for 30 test recipes; zero invented nutrient values.

## Run it locally

```bash
uv sync
cp .env.example .env

# Windows:
copy .env.example .env

uv run uvicorn nutrinin.api.main:create_app --factory --reload
```

Then open [http://localhost:8000/docs](http://localhost:8000/docs)

## Checks

```bash
uv run pytest
uv run ruff check .
```

>>>>>>> 52b2e02d1f3822550e1473558dcd1c3490b6f5d6
