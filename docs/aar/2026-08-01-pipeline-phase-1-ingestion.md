---
id: 2026-08-01-pipeline-phase-1-ingestion
date: 2026-08-01
title: Pipeline Phase 1 — Primary ingestion (FRE, ANBIMA, B3)
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Pipeline Phase 1 — Primary ingestion

## 1. Plan / purpose / objective

Implement roadmap Phase 1 (IMP-020..022): CVM FRE ingest, ANBIMA debentures/CRI/CRA, B3 shares/mcap + Balcão bonds, CLI sync stages, tests, and wire optional stages into `sync_pilot`.

## 2. What actually happened

- Added `src/decifra/cvm/fre.py` with zip download, field map, per-ticker `fre/` extracts.
- Added `src/decifra/anbima/` (fixture/cache CSV → `debt/anbima_instruments.csv`).
- Added `src/decifra/b3/` (`b3_shares.json`, Balcão bonds → company `debt/`).
- CLI: `decifra sync fre|anbima|b3-shares|b3-bonds`.
- `sync_pilot` accepts pipeline stages; default remains core four stages.
- Tests: `tests/test_pipeline_phase1.py` (4 passed).
- Smoke: ANBIMA + B3 Balcão wrote PETR4 debt rows; B3 shares artifact updated.

## 3. Gaps

- Live FRE zip layout varies by year; full-universe FRE sync needs cache warm-up (`--cache-only` when zips present).
- Official B3 share-count network detail API not fully wired (`use_network` reserved); artifact is local-meta based.
- ANBIMA/Balcão rely on cache/fixture files until stable public feeds are locked.

## 4. Lessons

- Keep pipeline sync stages opt-in on `sync_pilot` so daily pilots do not download FRE/funds by default.
- Fixture-backed FI parsers unblock CI and lake shape before opaque vendor APIs stabilize.
- Avoid Unicode arrows in Rich CLI strings on Windows cp1252 consoles.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-020 | CVM FRE zip ingest | high | done |
| IMP-021 | ANBIMA debt instruments | high | done |
| IMP-022 | B3 shares + Balcão | high | done |
| IMP-034 | Wire live B3 shares-outstanding detail API into `b3/shares.py` | med | open |
