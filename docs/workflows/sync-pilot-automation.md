# Cursor Automation: sync_pilot (IMP-008 / AUTO-001)

Wrap `scripts/sync_pilot.py` so scheduled or manual Automations always leave an automation AAR + refreshed session dashboard.

## Suggested Automation draft

| Field | Value |
|-------|--------|
| Name | Sync pilot (Ibovespa lake) |
| Trigger | Manual, or schedule (e.g. weekly) |
| Tools | Shell / terminal in this repo |
| Instructions | Run `.\.venv\Scripts\python.exe scripts/sync_pilot.py` from the repo root (Windows). Prefer dry-run flags only if the Automation prompt says so. On completion, confirm `docs/aar/automation/` gained a new AAR and `docs/dashboard/index.html` was refreshed. Do not push. Log product gaps to `docs/improvements/LOG.md` and automation meta to `docs/improvements/AUTOMATION.md`. |
| To finish in editor | Confirm git repo scope = this GitHub repo; set schedule if desired; enable network for CVM downloads |

## Local equivalent (no Automation UI)

```bash
.\.venv\Scripts\python.exe scripts/sync_pilot.py
```

## Status

Product IMP-008 / AUTO-001: draft documented here. Creating the live Cursor Automation requires finishing in the Automations editor (Agents Window) after user approval of the draft table.
