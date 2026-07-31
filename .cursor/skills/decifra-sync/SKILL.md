---
name: decifra-sync
description: >-
  Run and QA decifra-invest-agent Ibovespa data collection (decifra sync / sync_pilot).
  Use when syncing universe, financials, notices, transcripts, checking
  coverage, or automating data collection.
---

# decifra-invest-agent sync

## Invoke (Windows venv)

```bash
.\.venv\Scripts\python.exe -m decifra sync universe
.\.venv\Scripts\python.exe -m decifra sync financials
.\.venv\Scripts\python.exe -m decifra sync notices
.\.venv\Scripts\python.exe -m decifra sync transcripts
.\.venv\Scripts\python.exe -m decifra sync all
.\.venv\Scripts\python.exe -m decifra status
```

## Pilot automation runner

Preferred for documented collection runs (AAR + **required** dashboard refresh):

```bash
.\.venv\Scripts\python.exe scripts/sync_pilot.py
.\.venv\Scripts\python.exe scripts/sync_pilot.py --skip-transcripts
.\.venv\Scripts\python.exe scripts/sync_pilot.py --stages universe,financials
.\.venv\Scripts\python.exe scripts/sync_pilot.py --dry-run
```

See `docs/workflows/sync-pilot.md`, `docs/agents/sync-qa.md`, and `docs/improvements/AUTOMATION.md`.

## Known gaps (do not treat as surprises)

- **ASAI3**: may lack financial CSVs (IMP-002 — known CVM gap)
- **prices.csv**: backfilled (IMP-001 done); treat new misses as regressions
- CVM ZIP cache may be a subset of configured year defaults (IMP-003)

## Spot-check

PETR4, VALE3, ITUB4 — financials + notices + transcripts indexes.
