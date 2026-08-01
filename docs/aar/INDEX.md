# AAR index

Session and automation After Action Reports for decifra-invest-agent.

| Date | ID | Title | Type | Status | File |
|------|-----|-------|------|--------|------|
| 2026-08-01 | 2026-08-01-pipeline-phase-5-schemas-ui | Pipeline Phase 5 — Schemas & React MVP | agent | completed | [2026-08-01-pipeline-phase-5-schemas-ui.md](2026-08-01-pipeline-phase-5-schemas-ui.md) |
| 2026-08-01 | 2026-08-01-pipeline-phase-4-funds | Pipeline Phase 4 — Fund exposure | agent | completed | [2026-08-01-pipeline-phase-4-funds.md](2026-08-01-pipeline-phase-4-funds.md) |
| 2026-08-01 | 2026-08-01-pipeline-phase-3-modeling | Pipeline Phase 3 — Modeling engines | agent | completed | [2026-08-01-pipeline-phase-3-modeling.md](2026-08-01-pipeline-phase-3-modeling.md) |
| 2026-08-01 | 2026-08-01-pipeline-phase-2-entities | Pipeline Phase 2 — Entity resolution | agent | completed | [2026-08-01-pipeline-phase-2-entities.md](2026-08-01-pipeline-phase-2-entities.md) |
| 2026-08-01 | 2026-08-01-pipeline-phase-1-ingestion | Pipeline Phase 1 — Primary ingestion | agent | completed | [2026-08-01-pipeline-phase-1-ingestion.md](2026-08-01-pipeline-phase-1-ingestion.md) |
| 2026-08-01 | 2026-08-01-unified-pipeline-toolkit | Unified pipeline gap audit + toolkit install | agent | completed | [2026-08-01-unified-pipeline-toolkit.md](2026-08-01-unified-pipeline-toolkit.md) |
| 2026-07-20 | 2026-07-20-greenfield-pipeline | Greenfield Ibovespa pipeline | agent | completed | [2026-07-20-greenfield-pipeline.md](2026-07-20-greenfield-pipeline.md) |
| 2026-07-20 | 2026-07-20-credit-dashboard | Creditworthiness Streamlit dashboard | agent | completed | [2026-07-20-credit-dashboard.md](2026-07-20-credit-dashboard.md) |
| 2026-07-31 | 2026-07-31-report-platform-plan | Report platform planning | agent | superseded | [2026-07-31-report-platform-plan.md](2026-07-31-report-platform-plan.md) |
| 2026-07-31 | 2026-07-31-report-builder | Shared credit/equity report builder | agent | completed | [2026-07-31-report-builder.md](2026-07-31-report-builder.md) |
| 2026-07-31 | 2026-07-31-automation-aar | Automation + AAR memory | agent | completed | [2026-07-31-automation-aar.md](2026-07-31-automation-aar.md) |
| 2026-07-31 | 2026-07-31-rename-and-github | Rename workspace + push to GitHub | agent | completed | [2026-07-31-rename-and-github.md](2026-07-31-rename-and-github.md) |
| 2026-07-31 | 2026-07-31-implement-future-agent-prompts | Implement all FUTURE_AGENTS prompts | agent | completed | [2026-07-31-implement-future-agent-prompts.md](2026-07-31-implement-future-agent-prompts.md) |
| 2026-07-31 | 2026-07-31-dashboard-refresh | Refresh session dashboard (live coverage) | agent | completed | [2026-07-31-dashboard-refresh.md](2026-07-31-dashboard-refresh.md) |
| 2026-07-31 | 2026-07-31-automation-dashboard-track | Automation closeout + automation opportunity tracking | agent | completed | [2026-07-31-automation-dashboard-track.md](2026-07-31-automation-dashboard-track.md) |
| 2026-07-31 | 2026-07-31-credit-report-generation | Credit report HTML generation from prompt | agent | completed | [2026-07-31-credit-report-generation.md](2026-07-31-credit-report-generation.md) |
| 2026-07-31 | 2026-07-31-valuation-capability | Valuation capability (DCF + trading multiples) | agent | completed | [2026-07-31-valuation-capability.md](2026-07-31-valuation-capability.md) |

## Automation traces

| Date | ID | Title | Status | File |
|------|-----|-------|--------|------|
| 2026-07-31 | 2026-07-31-sync-pilot-dry-run | Sync pilot | completed | [2026-07-31-sync-pilot-dry-run.md](automation/2026-07-31-sync-pilot-dry-run.md) |
| 2026-07-31 | 2026-07-31-sync-pilot | Sync pilot | completed | [2026-07-31-sync-pilot.md](automation/2026-07-31-sync-pilot.md) |
| _(populated by `scripts/sync_pilot.py`)_ | | | | |

## How to add an AAR

1. Copy [`_TEMPLATE.md`](_TEMPLATE.md) to `YYYY-MM-DD-<slug>.md` (or `automation/YYYY-MM-DD-<slug>.md`).
2. Fill sections 1–5 (plan, happened, gaps, lessons, improvements).
3. Append improvements to [`../improvements/LOG.md`](../improvements/LOG.md) and/or [`../improvements/AUTOMATION.md`](../improvements/AUTOMATION.md).
4. Add a row to this INDEX.
5. Run `python scripts/update_session_dashboard.py` to refresh the human HTML dashboard (sync_pilot does this automatically).
