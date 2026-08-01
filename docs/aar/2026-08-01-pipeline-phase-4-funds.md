---
id: 2026-08-01-pipeline-phase-4-funds
date: 2026-08-01
title: Pipeline Phase 4 — Fund exposure (CVM + EDGAR)
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Pipeline Phase 4 — Fund exposure

## 1. Plan / purpose / objective

Implement IMP-029/030: CVM INF_DIARIO + CDA lake writers and SEC EDGAR exposure snapshot; flesh daily fund sync workflow; opt-in sync_pilot stages.

## 2. What actually happened

- Added `src/decifra/funds/cvm.py` and `edgar.py`.
- CLI: `decifra sync funds|edgar`.
- Workflow `daily-market-fund-sync.md` updated from stub.
- Pilot stages include `funds` and `edgar` (opt-in).
- Tests: `tests/test_pipeline_phase4.py`.

## 3. Gaps

- Live CVM fund zips are large; default path is fixture/cache (`--network` to download).
- EDGAR network path is best-effort browse-edgar; sample fixture is default.
- AUTO-008 Cursor Automation wrap still open.

## 4. Lessons

- Keep fund/EDGAR sync offline-default so CI and agents do not pull multi-GB CVM FI dumps accidentally.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-029 | CVM INF_DIARIO + CDA | med | done |
| IMP-030 | SEC EDGAR exposure | low | done |
| AUTO-008 | Daily fund sync Automation wrap | med | open |
