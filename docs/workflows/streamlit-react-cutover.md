# Streamlit → React cutover gates

Parity checklist before retiring the Streamlit research UI (`decifra dashboard`) in favor of the Terminal Dark React shell (`frontend/`).

Related: IMP-039 · IMP-037 (live feed) · IMP-038 (screener assembly).

## Must-pass gates

| # | Gate | How to verify | Owner surface |
|---|------|---------------|---------------|
| 1 | **Credit table parity** | Same industry filter + peer ranks as Streamlit Credit tab for Energy (PETR4 present, score finite) | React Credit view or screener credit cols vs `decifra credit --industry Energy` |
| 2 | **Valuation DCF parity** | PETR4 DCF equity value / per-share within ~1% of Streamlit Valuation tab (same assumption overrides) | React Waterfall/APV + CLI `decifra valuation dcf` |
| 3 | **Report builder export** | Can export `report.prompt.md` + `context.json` without Streamlit (CLI already; React optional) | `decifra report build` |
| 4 | **Live lake feed** | React does not depend on hand-edited `public/sample/*` for a demo ticker; `/api/...` or `decifra schemas export-ui` refreshes from lake | IMP-037 |
| 5 | **Screener from engines** | Opportunity screener rows come from APV + Merton + capacity assemblers, not hard-coded fixtures | IMP-036 / IMP-038 |
| 6 | **Lineage freshness** | Every metric cell shows source freshness string (ITR/ANBIMA/…) | Terminal Dark UX rule |
| 7 | **Identity enrichment** | Profile shows CNPJ + ISINs from `load_identity` / entities.json | IMP-035 |
| 8 | **Smoke suite green** | `pytest tests/test_credit.py tests/test_valuation_*.py tests/test_pipeline_phase*.py tests/test_report_*.py -q` | CI / local |
| 9 | **Ops runbook** | README documents `decifra ui` (npm ensure + schemas serve + Vite); manual `npm run dev` + `schemas serve` / export-ui still documented | docs |

## Nice-to-have (non-blocking)

- Multiples heatmap parity with Streamlit Plotly grid
- Qualitative signal scan surfaced in catalyst feed
- Auth / multi-user (out of scope for research MVP)

## Cutover decision

When gates **1–9** pass on a clean lake snapshot:

1. Mark Streamlit as deprecated in README (keep install extra for one release).
2. Default `decifra dashboard` help text → points at React + serve/export.
3. Close IMP-039 as done; open a follow-up only if analyst regressions appear.
