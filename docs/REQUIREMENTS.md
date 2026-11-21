# Requirements: NutriNIN

## Functional (what it does)

1. A user can ask a question in plain English and get an answer drawn from my trusted NIN and IFCT sources.
2. Every answer cites the document and page, table or section it came from.
3. If the documents do not contain the answer, the product says "I don't know" instead of guessing.
4. Signature feature: Weekly menu scorecard: paste a 7-day menu and see protein, iron, fibre and vegetable portions against the NIN plate for each day.
5. A user can browse and search the underlying records through GET /v1/documents.

## Non-functional (how well, with numbers)

| # | Quality | Target | How I will measure it |
|---|---|---|---|
| 1 | Speed: record lookups | p95 under 200 ms for GET /v1/documents | Load test with 100 concurrent users (Week 6) |
| 2 | Speed: answers | p95 under 5 seconds for a full answer; first token under 2 seconds | Application traces (Week 5) |
| 3 | Accuracy | Nutrient numbers within 5% of a hand calculation for 30 test recipes; zero invented nutrient values | Golden question set and recipe validation (Weeks 4 and 5) |
| 4 | Cost | Under ₹0.25 per answered question | Track actual API usage and costs in the llm_calls table (Week 2) |
| 5 | Availability | 99% monthly uptime of the live URL | Automated uptime monitoring from Day 5 |

## Target Justifications

- Record lookup target changed from 300 ms to 200 ms to make document searches feel responsive during regular mess operations.
- Answer latency target changed from 4 seconds to 5 seconds to allow source retrieval, citation generation and accurate nutritional calculations.
- Cost target changed from ₹0.50 to ₹0.25 to encourage efficient API usage and keep the product affordable for a hostel environment.
- Accuracy remains within 5% because reliable nutrient calculations are the core purpose of NutriNIN.
