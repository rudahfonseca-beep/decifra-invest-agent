---
id: 2026-08-01-ui-load-performance
date: 2026-08-01
title: React / lake API load performance
session_type: agent
transcript_id: ""
status: completed
---

# AAR: React / lake API load performance

## 1. Plan / purpose / objective

Reduce React Terminal Dark loading screens and empty-list flashes by fixing lake-API defaults/caches and splitting frontend fetches (shell vs ticker-scoped), with stale-while-revalidate UI.

## 2. What actually happened

- Added `schemas/ui_cache.py`: dual credit DataFrame cache (`sig=False` / `sig=True`) + TTL cache helpers.
- Screener/catalyst assemblies and profile/debt/waterfall endpoints use TTL cache; `/api/catalysts` reuses screener cache.
- API defaults for research list endpoints now `signals=false` (opt-in expensive scan).
- React `App.tsx`: mount-once shell load (screener/catalysts/industries/tickers); ticker change only reloads profile/debt/waterfall; progressive “refreshing…” instead of blanking tables.
- Tests: `tests/test_ui_cache.py` (mocked, fast); `npm run build` green.

## 3. Gaps

- No on-disk UI bundle refresh in sync_pilot yet (`schemas export-ui` still manual).
- Screener still serial per ticker on cold cache (APV+Merton+capacity); TTL only helps warm hits.
- Streamlit dashboard path unchanged (cutover checklist still open).

## 4. Lessons

- Never bind universe list fetches to `selectedTicker`.
- Keep fundamental and signal credit tables in separate cache slots.
- Default API `signals` must match the UI opt-in checkbox default.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-040 | Dual credit cache + screener TTL + React load split / SWR | high | done |
| IMP-041 | Persist UI JSON bundle on sync_pilot closeout (`export-ui`) | med | open |
| IMP-042 | Parallelize cold screener row assembly (thread pool) | low | open |
