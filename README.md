# NutriNIN

[![CI](https://github.com/simsonson/prince28-hlt06-nutrinin/actions/workflows/ci.yml/badge.svg)](https://github.com/simsonson/prince28-hlt06-nutrinin/actions/workflows/ci.yml)

[![Live](https://img.shields.io/website?url=https%3A%2F%2Fnutrinin.onrender.com%2Fhealth&label=live)](https://nutrinin.onrender.com/docs)

[![UptimeRobot](https://img.shields.io/uptimerobot/status/m804746196-5599f26d33790f04536ebac6)](https://nutrinin.onrender.com/health)

![Uptime (30 Days)](https://img.shields.io/uptimerobot/ratio/m804746196-5599f26d33790f04536ebac6)

**Live:** [https://nutrinin.onrender.com](https://nutrinin.onrender.com) · [API docs](https://nutrinin.onrender.com/docs) · [health](https://nutrinin.onrender.com/health)

**Status:** Week 1 complete · live at https://nutrinin.onrender.com


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
## Run locally in one command

You need Docker Desktop running. From a fresh clone:

```bash
docker compose up --build
```

This starts Postgres (with pgvector), Redis, runs the migrations and loads the sample data once, then starts the API.

- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/health
- Readiness (checks the database): http://localhost:8000/ready

Stop with `Ctrl+C`, then `docker compose down`. Add `-v` to also delete the database volume.

## Develop and test

| Task | Mac / Linux | Windows |
|---|---|---|
| Run the API with reload | `make dev` | `uv run poe dev` |
| Unit tests (no network) | `make test` | `uv run poe test` |
| Integration tests (needs `docker compose up`) | `make test-integration` | `uv run poe test-integration` |
| Coverage report | `make cov` | `uv run poe cov` |
| Lint and format check | `make lint` | `uv run poe lint` |
