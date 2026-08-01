# Workflow: Daily market & fund sync (stub)

**Status:** Planned — not implemented. Tracked as `AUTO-008`.  
**Roadmap:** Phase 4 (+ ANBIMA curves from Phase 1).

## Purpose

Daily fetch of:

- CVM Funds **INF_DIARIO** (NAV / AUM)
- ANBIMA secondary market pricing / yield curves (when Phase 1 ANBIMA client exists)

## Intended CLI (future)

```bash
.\.venv\Scripts\python.exe -m decifra sync funds --daily
.\.venv\Scripts\python.exe -m decifra sync anbima --curves
# Preferred once wired:
.\.venv\Scripts\python.exe scripts/sync_pilot.py --stages funds,anbima-curves
```

## Lake targets

- `data/funds/` — INF_DIARIO cache + derived NAV series
- `data/cache/anbima/` — curve / secondary snapshots

## Closeout

Every automated run must write an automation AAR under `docs/aar/automation/` and refresh the session dashboard (`scripts/update_session_dashboard.py`), same pattern as `sync_pilot.py`.

## Do not

- Claim daily fund sync works until modules and lake artifacts exist
- Skip AAR/dashboard refresh on scheduled runs
