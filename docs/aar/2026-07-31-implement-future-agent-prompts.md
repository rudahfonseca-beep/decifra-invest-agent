---
id: 2026-07-31-implement-future-agent-prompts
date: 2026-07-31
title: Implement all FUTURE_AGENTS prompts
session_type: agent
transcript_id: "ac8c1a19-4413-4325-b215-8cd1ef4ef178"
status: completed
---

# AAR: Implement all FUTURE_AGENTS prompts

## 1. Plan / purpose / objective

Execute all 9 prompts from [`docs/prompts/FUTURE_AGENTS.md`](../prompts/FUTURE_AGENTS.md), covering data collection, credit fixes, sector normalization, offline report building, price backfilling, ASAI3 diagnosis, and session hygiene.

## 2. What actually happened

- **Prompt 4 (Interest coverage fix - IMP-004)**: Added `3.06.02` (`interest_expense` / Despesas Financeiras) sub-account mapping in `src/decifra/credit/metrics.py`. Fixed PETR4 interest coverage when parent `3.06` is net positive. Added 2 regression tests in `tests/test_credit.py`.
- **Prompt 5 (Sector normalization - IMP-007)**: Expanded `SECTOR_TO_GROUP` in `src/decifra/credit/scoring.py` from ~30 to ~47 mappings (Gás, Construção Civil, Securitizadoras, Logística, Açúcar e Álcool, etc.). Added unit tests.
- **Prompt 8 (Offline HTML render - IMP-012)**: Created `src/decifra/report/render_offline.py` (Jinja2 + Plotly CDN renderer), added `--offline` flag to `decifra report build`, added `jinja2` dependency in `pyproject.toml`, and created `tests/test_report_offline.py`.
- **Prompt 3 (ASAI3 diagnosis - IMP-002)**: Created `scripts/diagnose_asai3.py`. Confirmed ASAI3/Sendas (CNPJ `06057223000171`) has 2020 DFP data, but 2021+ is absent in CVM DFP dumps following the GPA spinoff. Documented in `docs/improvements/LOG.md`.
- **Prompt 2 (Prices backfill - IMP-001)**: Created `scripts/backfill_prices.py`. Backfilled 10-year OHLCV prices for 52 missing tickers using `BRAPI_API_KEY` (100% success, 52/52). Spot-checked PETR4, VALE3, ITUB4 (2,482 rows each).
- **Prompt 6 (Credit smoke)**: Verified `decifra credit --industry Energy` (13 companies scored, peer benchmarks active).
- **Prompt 7 (Report build smoke)**: Verified all 32 pytest unit tests pass and `decifra report build --mode credit --company PETR4 --industry Energy --offline` generates valid HTML reports.
- **Prompt 1 (Sync pilot)**: Launched `scripts/sync_pilot.py` for automated Ibovespa collection.

## 3. Gaps

- ASAI3 DFP data from 2021 onwards remains missing due to upstream CVM dump absence post-GPA spinoff (documented as known CVM gap in IMP-002).

## 4. Lessons

- `3.06.02` sub-account mapping is critical for interest coverage on companies whose financial revenue exceeds expenses (making parent `3.06` net positive).
- `BRAPI_API_KEY` enables fast, complete OHLCV price backfills (2,482 bars/ticker) across the entire Ibovespa universe in under 2 minutes.
- Jinja2 + Plotly offline rendering allows zero-latency interactive HTML reports without LLM API dependency.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-001 | Backfill prices.csv for all Ibovespa tickers | high | completed |
| IMP-002 | Investigate ASAI3 missing DFP/ITR financials | high | completed |
| IMP-004 | Fix empty interest coverage for PETR4 | high | completed |
| IMP-007 | Normalize free-text sectors into stable industry groups | med | completed |
| IMP-012 | Optional offline HTML render from context.json | low | completed |

See [`docs/improvements/LOG.md`](../improvements/LOG.md).
