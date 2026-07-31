# Subagent playbook: Credit QA

## Goal

Smoke-test industry peer credit scores and catch empty-metric regressions.

## Before exploring

Read `docs/workflows/credit-smoke.md` and the credit AAR (`2026-07-20-credit-dashboard.md`).

## Procedure

1. Ensure financials exist for the industry under test.
2. Run:

```bash
.\.venv\Scripts\python.exe -m decifra credit --industry Energy
```

3. Check for empty or null interest coverage / leverage ratios on large names (PETR4).
4. Optional: open Streamlit (`decifra dashboard`) and verify Industry overview + Data coverage tabs.
5. If a metric bug is found, fix with a regression test under `tests/`, then AAR + improvements LOG.

## Caveats

- Scores are research-grade peer ranks, not Serasa/bureau ratings.
- Bank/insurer vs non-financial scorecards differ.
