# Improvements log

Lessons from AARs turned into trackable follow-ups. Newest first within each status.

**Automation meta-opportunities** (runners, closeout, dashboard freshness, Cursor Automations) live in [`AUTOMATION.md`](AUTOMATION.md) as `AUTO-*` rows — keep this file for product/data gaps (`IMP-*`).

## Open

| ID | Date | Source AAR | Improvement | Priority | Notes |
|----|------|------------|-------------|----------|-------|
| IMP-013 | 2026-07-31 | rename-and-github | Rename local folder `DecifraCR` -> `decifra-invest-agent` after closing Cursor; re-run editable install | med | Dir locked while workspace open — human step |

## Done

| ID | Date | Source AAR | Improvement | Resolved |
|----|------|------------|-------------|----------|
| IMP-038 | 2026-08-01 | terminal-dark-ui / backlog-close | Assemble screener rows from APV + Merton + capacity | 2026-08-01 -- `schemas/screener.py` + `schemas screener\|export-ui` |
| IMP-039 | 2026-08-01 | terminal-dark-ui / backlog-close | Streamlit → React cutover gates | 2026-08-01 -- `docs/workflows/streamlit-react-cutover.md` |
| IMP-037 | 2026-08-01 | pipeline-phase-5 / backlog-close | Live lake/API feed for React UI | 2026-08-01 -- `schemas/api_server.py` + `schemas serve` + Vite `/api` proxy |
| IMP-036 | 2026-08-01 | pipeline-phase-3 / backlog-close | Auto-assemble APV/Merton/capacity from ticker | 2026-08-01 -- `valuation/assemble_apv.py` + `credit/assemble_models.py` + CLI `--ticker` |
| IMP-035 | 2026-08-01 | pipeline-phase-2 / backlog-close | Migrate credit/valuation/report joins to `load_identity` | 2026-08-01 -- metrics/scoring/multiples/report + store export |
| IMP-034 | 2026-08-01 | pipeline-phase-1 / backlog-close | Wire live B3 shares API | 2026-08-01 -- `GetListedSupplementCompany` + `sync b3-shares --network` |
| IMP-018 | 2026-08-01 | valuation / backlog-close | Cache Valuation tab `sensitivity_grid` | 2026-08-01 -- `@st.cache_data` in dashboard |
| IMP-017 | 2026-07-31 | valuation-capability | Open PR for `feat/valuation-dashboard-docs` | 2026-08-01 -- PR #6 opened (later closed; Valuation tab on `main`) |
| IMP-016 | 2026-08-01 | valuation / backlog-close | Extreme upside callout | 2026-08-01 -- Streamlit + `valuation.md` + workflow doc |
| IMP-015 | 2026-08-01 | valuation / backlog-close | EPS/mcap implied shares fallback | 2026-08-01 -- `market_data.py` (B3 artifact → mcap/price → NI/EPS) |
| IMP-008 | 2026-08-01 | automation-aar / backlog-close | Wrap `sync_pilot.py` in Cursor Automation | 2026-08-01 -- draft in Automations editor + `docs/workflows/sync-pilot-automation.md` |
| IMP-003 | 2026-08-01 | greenfield / backlog-close | Expand CVM cache years (2020-2021 DFP/ITR; notices) | 2026-08-01 -- DFP/ITR already cached; IPE 2020-2022 warmed; `DEFAULT_NOTICE_YEARS` → 2020-2026 |
| IMP-031 | 2026-08-01 | pipeline-phase-5-schemas-ui | Phase 5: Three schemas + lineage | 2026-08-01 -- `schemas/` + `docs/schemas/` |
| IMP-032 | 2026-08-01 | pipeline-phase-5-schemas-ui | Phase 5: ITR–debt DT_REFER alignment | 2026-08-01 -- `schemas/alignment.py` |
| IMP-033 | 2026-08-01 | pipeline-phase-5-schemas-ui | Phase 5: React dark-mode MVP | 2026-08-01 -- `frontend/` |
| IMP-029 | 2026-08-01 | pipeline-phase-4-funds | Phase 4: CVM INF_DIARIO + CDA | 2026-08-01 -- `funds/cvm.py` |
| IMP-030 | 2026-08-01 | pipeline-phase-4-funds | Phase 4: SEC EDGAR exposure | 2026-08-01 -- `funds/edgar.py` |
| IMP-025 | 2026-08-01 | pipeline-phase-3-modeling | Phase 3: APV engine | 2026-08-01 -- `valuation/apv.py` |
| IMP-026 | 2026-08-01 | pipeline-phase-3-modeling | Phase 3: Merton / DtD | 2026-08-01 -- `credit/merton.py` |
| IMP-027 | 2026-08-01 | pipeline-phase-3-modeling | Phase 3: Debt capacity flags | 2026-08-01 -- `credit/capacity.py` |
| IMP-028 | 2026-08-01 | pipeline-phase-3-modeling | Phase 3: OCF→FCFE waterfall | 2026-08-01 -- `valuation/waterfall.py` |
| IMP-023 | 2026-08-01 | pipeline-phase-2-entities | Phase 2: Entity graph CNPJ↔CVM↔ticker↔ISIN | 2026-08-01 -- `entities/` + `entities sync` |
| IMP-024 | 2026-08-01 | pipeline-phase-2-entities | Phase 2: Hierarchy of Truth + private-issuer fallback | 2026-08-01 -- resolve + CLI + workflow |
| IMP-020 | 2026-08-01 | pipeline-phase-1-ingestion | Phase 1: CVM FRE zip ingest + company extracts | 2026-08-01 -- `cvm/fre.py` + `decifra sync fre` |
| IMP-021 | 2026-08-01 | pipeline-phase-1-ingestion | Phase 1: ANBIMA debentures/CRI/CRA | 2026-08-01 -- `anbima/` + cache/fixture sync |
| IMP-022 | 2026-08-01 | pipeline-phase-1-ingestion | Phase 1: B3 shares/mcap + Balcão bonds | 2026-08-01 -- `b3/` + CLI stages |
| IMP-001 | 2026-07-20 | greenfield-pipeline | Backfill `prices.csv` for all Ibovespa tickers | 2026-07-31 -- BRAPI backfill via `scripts/backfill_prices.py`; lake now 78/78 |
| IMP-014 | 2026-07-31 | dashboard-refresh | Session dashboard coverage from live lake (not stale automation AAR) + clean prompt parse | 2026-07-31 |
| IMP-002 | 2026-07-20 | greenfield-pipeline | Investigate ASAI3 missing DFP/ITR financials; document if CVM dump gap | 2026-07-31 -- CNPJ 06057223000171 (Sendas) maps correctly, DFP has 2020 data only; 2021+ absent after GPA spinoff. Known CVM gap. |
| IMP-004 | 2026-07-20 | credit-dashboard | Fix empty interest coverage for PETR4 (account alias mapping) + regression test | 2026-07-31 -- Added 3.06.02 (interest_expense) sub-account with desc fallback; two regression tests |
| IMP-005 | 2026-07-20 | credit-dashboard | Document Windows venv PATH: always use `.\.venv\Scripts\` | 2026-07-31 (`.cursor/rules/windows-venv.mdc`) |
| IMP-006 | 2026-07-31 | report-platform-plan / report-builder | Choose delivery mode then implement report builder | 2026-07-31 -- LLM prompt pack + shared builder |
| IMP-007 | 2026-07-31 | report-platform-plan | Normalize free-text sectors into stable industry groups | 2026-07-31 -- Expanded SECTOR_TO_GROUP from ~30 to ~47 entries; tests |
| IMP-009 | 2026-07-31 | automation-aar | Add AAR markdown + human HTML dashboard + session closeout rule | 2026-07-31 |
| IMP-010 | 2026-07-31 | automation-aar | Add local sync pilot runner with coverage delta + automation AAR | 2026-07-31 |
| IMP-011 | 2026-07-31 | report-builder | Document report workflow / skill / QA playbook | 2026-07-31 |
| IMP-012 | 2026-07-31 | report-builder | Optional offline HTML render from `context.json` (no LLM) | 2026-07-31 -- `render_offline.py` + `--offline` CLI flag + Jinja2+Plotly |
| IMP-019 | 2026-07-31 | valuation-capability | Fix 1000x DCF/multiples value error: CVM reports monetary accounts in thousands of reais; `valuation/historical.py` now normalizes to absolute reais to match market data | 2026-07-31 -- caught via manual PETR4 smoke test, not unit tests; backported to PR #2/#3 |
