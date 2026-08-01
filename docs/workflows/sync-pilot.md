# Workflow: Sync pilot

Automates the existing data collection (`decifra sync …`) and writes an automation AAR.

## Prerequisites

- Project venv installed: `pip install -e ".[dev]"` inside `.venv`
- Network access to B3 / CVM / price providers

## Steps

```bash
# Full staged sync (universe → financials=all → notices/transcripts=core)
.\.venv\Scripts\python.exe scripts/sync_pilot.py

# Faster iteration
.\.venv\Scripts\python.exe scripts/sync_pilot.py --skip-transcripts
.\.venv\Scripts\python.exe scripts/sync_pilot.py --stages universe,financials
.\.venv\Scripts\python.exe scripts/sync_pilot.py --financials-scope core --heavy-scope core
.\.venv\Scripts\python.exe scripts/sync_pilot.py --skip-ui-export
.\.venv\Scripts\python.exe scripts/sync_pilot.py --dry-run
```

Tiered defaults: financials use `--scope all`; notices/transcripts/fre/anbima/b3-bonds use `--scope core` (IBOV ∪ watchlist).

The runner:

1. Captures coverage **before**
2. Runs selected sync stages (with tiered `--scope`)
3. Captures coverage **after**
4. Writes `docs/aar/automation/YYYY-MM-DD-sync-pilot.md`
5. Updates `docs/aar/INDEX.md` automation section
6. **Required:** refreshes `docs/dashboard/index.html` via `scripts/update_session_dashboard.py` (non-zero exit if refresh fails)
7. Unless `--skip-ui-export` / `--dry-run`: `schemas export-ui` + `schemas warm-ui-cache` (IMP-041)
8. Surfaces automation opportunities in the AAR (standing `AUTO-*` + run notes); lasting items go in `docs/improvements/AUTOMATION.md`

## Skill / playbook

- Skill: `.cursor/skills/decifra-sync/SKILL.md`
- Playbook: `docs/agents/sync-qa.md`
- Automation opportunities: `docs/improvements/AUTOMATION.md`
