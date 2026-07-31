# Prompts for future agents

Copy-paste prompts. Prefer reading `docs/aar/INDEX.md` and `README.md` before exploring.

## Data collection

1. **Sync + coverage delta**  
   `Run the Ibovespa sync via .venv (python scripts/sync_pilot.py or staged decifra sync). Report coverage deltas vs the latest automation AAR. Fix only regressions; log remaining gaps to docs/improvements/LOG.md.`

2. **Prices backfill**  
   `Backfill prices.csv for all Ibovespa tickers missing OHLCV. Use BRAPI_API_KEY if present, else yfinance. Spot-check PETR4/VALE3/ITUB4. Write an AAR and update the HTML dashboard.`

3. **ASAI3 financials**  
   `Diagnose why ASAI3 has no income/balance/cash CSVs. Check CNPJ mapping and CVM DFP/ITR presence. Fix or document as a known CVM dump gap. Add a note to improvements LOG.`

## Credit / research

4. **Interest coverage fix**  
   `Diagnose empty interest_coverage for PETR4 in credit metrics. Fix account alias mapping; add a regression test; run credit smoke for Energy.`

5. **Sector normalization**  
   `Normalize free-text sectors into stable industry_group values used by credit scoring. Document the mapping and update tests.`

6. **Credit smoke**  
   `Follow docs/workflows/credit-smoke.md: run decifra credit --industry Energy, note empty ratios, write a short AAR if anything regresses.`

## Product

7. **Report build smoke**  
   `Follow docs/workflows/report-build.md: run pytest on test_report_*, then decifra report build for PETR4/Energy, inspect data/reports artifacts. Optional --generate if OPENAI_API_KEY is set.`

8. **Offline HTML from context (IMP-012)**  
   `Add an optional path that renders interactive HTML from context.json + chart_specs without calling an LLM (Jinja/Plotly). Keep prompt packing as the default path.`

## Session hygiene

9. **Session closeout**  
   `Write an AAR for this session using docs/aar/_TEMPLATE.md (plan / happened / gaps / lessons / improvements). Update docs/aar/INDEX.md, docs/improvements/LOG.md, and run python scripts/update_session_dashboard.py.`
