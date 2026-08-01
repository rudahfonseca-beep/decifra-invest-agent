# Automation improvement opportunities

Meta follow-ups about **how we automate** (runners, closeout, Cursor Automations, dashboard freshness) — separate from product/data gaps in [`LOG.md`](LOG.md).

Newest first within each status. IDs use `AUTO-NNN`. Cross-link product IMPs when relevant.

## Open

| ID | Date | Source | Opportunity | Priority | Notes |
|----|------|--------|-------------|----------|-------|
| AUTO-008 | 2026-08-01 | unified-pipeline-toolkit | Daily market & fund sync Automation (INF_DIARIO + ANBIMA curves) once runners exist — see `docs/workflows/daily-market-fund-sync.md` | med | Depends IMP-021 / IMP-029 |
| AUTO-009 | 2026-08-01 | unified-pipeline-toolkit | Quarterly earnings trigger: on new ITR/DFP detect → refresh 3-statements + models — `docs/workflows/quarterly-earnings-trigger.md` | med | Extends sync_pilot pattern |
| AUTO-010 | 2026-08-01 | unified-pipeline-toolkit | Private-issuer fallback runner Automation — `docs/workflows/private-issuer-fallback.md` | med | Depends IMP-024 |
| AUTO-003 | 2026-07-31 | dashboard-refresh | Prefer `sync_pilot` (or explicit closeout) over ad-hoc `decifra sync` so every collection run leaves AAR + dashboard | med | Ad-hoc sync skips traces |
| AUTO-004 | 2026-07-31 | dashboard-refresh | After lake mutations outside the pilot (backfills, diagnose scripts), always run `update_session_dashboard.py` | med | Stale coverage when agents skip closeout |

## Done

| ID | Date | Source | Opportunity | Resolved |
|----|------|--------|-------------|----------|
| AUTO-001 | 2026-08-01 | backlog-close / IMP-008 | Wrap `scripts/sync_pilot.py` in a Cursor Automation | 2026-08-01 — Automations editor prefilled; see `docs/workflows/sync-pilot-automation.md` (save in UI) |
| AUTO-002 | 2026-07-31 | automation-dashboard-track | Make session dashboard refresh a **required** sync-pilot closeout step (fail loudly if refresh fails) | 2026-07-31 — `sync_pilot.refresh_dashboard` checks rc |
| AUTO-005 | 2026-07-31 | dashboard-refresh / IMP-014 | Dashboard coverage must prefer live lake over frozen automation AAR snapshots | 2026-07-31 — `update_session_dashboard.live_coverage` |
| AUTO-006 | 2026-07-31 | sync-pilot | Stop hardcoding stale open IMPs inside generated automation AAR §5; point at LOG + AUTOMATION.md | 2026-07-31 — template derives from live gaps + AUTO rows |
| AUTO-007 | 2026-07-31 | automation-dashboard-track | Deduplicate automation INDEX rows when placeholder remains | 2026-07-31 — `update_index` skips if id already present |

## How to add

1. Append a row under **Open** with the next `AUTO-NNN` id.
2. Mention it in the automation or agent AAR §5 Improvements.
3. Run `.\.venv\Scripts\python.exe scripts/update_session_dashboard.py` (sync_pilot does this automatically).
