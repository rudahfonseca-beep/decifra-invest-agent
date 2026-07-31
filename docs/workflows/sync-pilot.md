# Workflow: Sync pilot

Automates the existing data collection (`decifra sync …`) and writes an automation AAR.

## Prerequisites

- Project venv installed: `pip install -e ".[dev]"` inside `.venv`
- Network access to B3 / CVM / price providers

## Steps

```bash
# Full staged sync (universe → financials → notices → transcripts)
.\.venv\Scripts\python.exe scripts/sync_pilot.py

# Faster iteration
.\.venv\Scripts\python.exe scripts/sync_pilot.py --skip-transcripts
.\.venv\Scripts\python.exe scripts/sync_pilot.py --stages universe,financials
.\.venv\Scripts\python.exe scripts/sync_pilot.py --dry-run
```

The runner:

1. Captures coverage **before**
2. Runs selected sync stages
3. Captures coverage **after**
4. Writes `docs/aar/automation/YYYY-MM-DD-sync-pilot.md`
5. Updates `docs/aar/INDEX.md` automation section
6. **Required:** refreshes `docs/dashboard/index.html` via `scripts/update_session_dashboard.py` (non-zero exit if refresh fails)
7. Surfaces automation opportunities in the AAR (standing `AUTO-*` + run notes); lasting items go in `docs/improvements/AUTOMATION.md`

## Skill / playbook

- Skill: `.cursor/skills/decifra-sync/SKILL.md`
- Playbook: `docs/agents/sync-qa.md`
- Automation opportunities: `docs/improvements/AUTOMATION.md`
