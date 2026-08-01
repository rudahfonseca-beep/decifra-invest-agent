# Prompts for future agents

Copy-paste prompts. Prefer reading `docs/aar/INDEX.md` and `README.md` before exploring.

Completed work (do not re-run unless regressing): prices backfill (IMP-001), ASAI3 diagnosis (IMP-002), interest coverage (IMP-004), sector normalization (IMP-007), offline HTML reports (IMP-012).

## Data collection

1. **Sync + coverage delta**  
   `Run Ibovespa sync via .venv using python scripts/sync_pilot.py (preferred — writes automation AAR and refreshes the session dashboard). Report coverage deltas. Fix only regressions; log product gaps to docs/improvements/LOG.md and automation meta to docs/improvements/AUTOMATION.md.`

2. **CVM cache years (IMP-003)**  
   `Expand CVM DFP/ITR/IPE cache years toward config defaults (include 2020-2021 where missing). Document what remains unavailable upstream.`

## Credit / research

3. **Credit smoke**  
   `Follow docs/workflows/credit-smoke.md: run decifra credit --industry Energy, note empty ratios, write a short AAR if anything regresses.`

## Product

4. **Report build smoke**  
   `Follow docs/workflows/report-build.md: run pytest on test_report_*, then decifra report build for PETR4/Energy (with --offline), inspect data/reports artifacts. Optional --generate if OPENAI_API_KEY is set.`

4b. **Valuation smoke**  
   `Follow docs/workflows/valuation.md: run pytest on test_valuation_*, then decifra valuation dcf/multiples/build for PETR4 vs VALE3,CSNA3. Sanity-check the DCF per-share value against the real current price (order of magnitude, not exact) — a scale mismatch between CVM's thousands-of-reais convention and market data's absolute reais silently produces a 1000x-wrong value (see IMP-019). Optional Streamlit "Valuation" tab check.`

4c. **Valuation follow-ups (IMP-015..018)**  
   `Pick one open item from docs/improvements/LOG.md tagged valuation-capability: EPS-implied shares fallback (IMP-015), extreme-upside UI callout (IMP-016), open the feat/valuation-dashboard-docs PR (IMP-017), or profile/cache the sensitivity grid (IMP-018).`

## Ops / hygiene

5. **Rename local folder (IMP-013)**  
   `After closing Cursor, rename DecifraCR -> decifra-invest-agent, reopen, re-run editable install, confirm decifra CLI.`

6. **Cursor Automation wrapper (AUTO-001 / IMP-008)**  
   `Optionally wrap scripts/sync_pilot.py in a Cursor Automation now that the repo is on GitHub. Dashboard refresh is already part of the pilot closeout.`

7. **Session closeout**  
   `Write an AAR for this session using docs/aar/_TEMPLATE.md (plan / happened / gaps / lessons / improvements). Update docs/aar/INDEX.md, docs/improvements/LOG.md and/or AUTOMATION.md, and run python scripts/update_session_dashboard.py.`
