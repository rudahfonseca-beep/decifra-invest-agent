# Subagent playbook: Report QA

## Goal

Smoke-test the shared report builder (spec → context → prompt → optional HTML) and catch regressions in catalog, assembly, or prompt packing.

## Before exploring

Read:

- `docs/workflows/report-build.md`
- `README.md` § Report builder
- AAR `docs/aar/2026-07-31-report-builder.md` (if present)

## Procedure

1. Confirm local financials for at least one subject ticker (`decifra status --ticker PETR4`).
2. Run unit tests:

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_report_*.py -q
```

3. Build a credit report (prompt only):

```bash
.\.venv\Scripts\python.exe -m decifra report build --mode credit --company PETR4 --industry Energy --no-signals
```

4. Inspect `data/reports/<latest>/context.json`:
   - `companies[].found` is true for subjects
   - `industries[].ranked_members` non-empty when an industry subject is set
   - `selected_kpis` matches mode defaults or CLI `--kpi`
5. Skim `report.prompt.md` for scaffold markers (`#narrative`, Plotly, disclaimer).
6. Optional: `--generate` with `OPENAI_API_KEY`; open `report.html` in a browser.
7. Optional UI: `decifra dashboard` → **Report builder** tab → Export prompt.

## Caveats

- Deliverable without LLM = packed prompt + context JSON (paste into any chat model).
- Equity mode is fundamentals/peer profitability — not DCF or target prices.
- Research-grade only; not a bureau rating.
- Unknown tickers/industries/KPIs must fail validation.

## On failure

Fix with a regression under `tests/test_report_*.py`, then AAR + `docs/improvements/LOG.md`.
