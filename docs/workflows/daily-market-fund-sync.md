# Workflow: Daily market & fund sync

**Status:** Runner modules implemented — Cursor Automation wrap still open (`AUTO-008`).  
**Roadmap:** Phase 4 (+ ANBIMA from Phase 1).

## Purpose

Daily fetch of:

- CVM Funds **INF_DIARIO** (NAV / AUM)
- CVM **CDA** (monthly holdings)
- ANBIMA secondary / debt cache refresh
- Optional SEC EDGAR ADR exposure snapshot

## CLI

```bash
.\.venv\Scripts\python.exe -m decifra sync funds --year 2026 --month 7
.\.venv\Scripts\python.exe -m decifra sync anbima
.\.venv\Scripts\python.exe -m decifra sync edgar
# Opt-in pilot stages:
.\.venv\Scripts\python.exe scripts/sync_pilot.py --stages funds,edgar,anbima --dry-run
```

Default `sync funds` uses fixture/cache (`from_cache_only`) to keep CI offline-green. Pass `--network` for live CVM zips.

## Lake targets

- `data/funds/{yyyymm}/inf_diario.csv`, `cda.csv`, `meta.json`
- `data/funds/edgar/exposure.json`
- `data/cache/anbima/` — debt instrument cache

## Closeout

Every automated run must write an automation AAR under `docs/aar/automation/` and refresh the session dashboard (`scripts/update_session_dashboard.py`), same pattern as `sync_pilot.py`.

## Do not

- Skip AAR/dashboard refresh on scheduled runs
- Claim AUTO-008 Cursor Automation is configured until wrapped
