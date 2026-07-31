# Improvements log

Lessons from AARs turned into trackable follow-ups. Newest first within each status.

## Open

| ID | Date | Source AAR | Improvement | Priority | Notes |
|----|------|------------|-------------|----------|-------|
| IMP-001 | 2026-07-20 | greenfield-pipeline | Backfill `prices.csv` for all Ibovespa tickers (currently ~3/78) | high | Prefer `BRAPI_API_KEY`; falls back to yfinance |
| IMP-002 | 2026-07-20 | greenfield-pipeline | Investigate ASAI3 missing DFP/ITR financials; document if CVM dump gap | high | 77/78 financial CSV sets |
| IMP-003 | 2026-07-20 | greenfield-pipeline | Expand CVM cache years toward config defaults (2020–2021 DFP/ITR; fato relevante) | med | Partial cache 2022–2025 |
| IMP-004 | 2026-07-20 | credit-dashboard | Fix empty interest coverage for PETR4 (account alias mapping) + regression test | high | See credit metrics |
| IMP-007 | 2026-07-31 | report-platform-plan | Normalize free-text sectors into stable industry groups | med | Improves peer cohorts |
| IMP-008 | 2026-07-31 | automation-aar | Optionally wrap `sync_pilot.py` in a Cursor Automation once repo is on remote | low | Local runner is pilot |
| IMP-012 | 2026-07-31 | report-builder | Optional offline HTML render from `context.json` (no LLM) | low | Prompt path is primary |
| IMP-013 | 2026-07-31 | rename-and-github | Rename local folder `DecifraCR` → `decifra-invest-agent` after closing Cursor; re-run editable install | med | Dir locked while workspace open |

## Done

| ID | Date | Source AAR | Improvement | Resolved |
|----|------|------------|-------------|----------|
| IMP-005 | 2026-07-20 | credit-dashboard | Document Windows venv PATH: always use `.\.venv\Scripts\` | 2026-07-31 (`.cursor/rules/windows-venv.mdc`) |
| IMP-006 | 2026-07-31 | report-platform-plan / report-builder | Choose delivery mode then implement report builder | 2026-07-31 — LLM prompt pack + shared builder |
| IMP-009 | 2026-07-31 | automation-aar | Add AAR markdown + human HTML dashboard + session closeout rule | 2026-07-31 |
| IMP-010 | 2026-07-31 | automation-aar | Add local sync pilot runner with coverage delta + automation AAR | 2026-07-31 |
| IMP-011 | 2026-07-31 | report-builder | Document report workflow / skill / QA playbook | 2026-07-31 |
