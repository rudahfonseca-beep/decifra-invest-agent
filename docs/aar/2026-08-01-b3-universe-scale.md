---
id: 2026-08-01-b3-universe-scale
date: 2026-08-01
title: Full B3 universe + scalable state (tiered)
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Full B3 universe + scalable state (tiered)

## 1. Plan / purpose / objective

Expand the lake from Ibovespa-only (~78) to all B3 listed equities with **tiered sync** (financials=all, heavy stages=core), harden lake-API + React state for hundreds of tickers, keep React+Vite as the Terminal Dark shell.

## 2. What actually happened

- Added [`src/decifra/universe/listed.py`](../../src/decifra/universe/listed.py): paginate `GetInitialCompanies` (type=1 active), `GetDetail` equity codes, merge IBOV + `watchlist.json` → `equities.json` with `sync_tier` / `indexes`.
- Migrated [`load_universe` / `list_tickers(scope=)`](../../src/decifra/store/folders.py) (equities.json with ibovespa.json fallback).
- CLI + sync stages accept `--scope all|core` with tiered defaults; `sync_pilot` passes scopes and runs IMP-041 export/warm on closeout.
- Disk UI cache under `data/cache/ui/` + `schemas warm-ui-cache`; screener parallelized (IMP-042); API defaults `scope=core` with `q`/`limit`/`offset`.
- React: TanStack Query + debounced ticker search + virtualized `DataTable` for long lists.
- Docs: README, sync-pilot workflow, data-sources rule, frontend README.

## 3. Gaps

- Live full-universe sync (568 issuers × GetDetail) not executed in-session (network time); unit tests cover parsing/scope.
- Streamlit cutover gates still open; Streamlit remains interim research UI.
- Virtualized HTML table rows use absolute positioning — OK for scroll performance, may need polish on very wide columns.

## 4. Lessons

- GetInitialCompanies returns issuers, not tickers; equity codes come from GetDetail `otherCodes` (filter `^[A-Z]{4}\d{1,2}$`).
- Scale wins are server-side (scope + disk cache + parallel assemble), not Redux.
- Never bind universe list fetches to `selectedTicker` (still true with Query keys).

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-041 | Persist UI JSON bundle on sync_pilot closeout | med | done |
| IMP-042 | Parallelize cold screener row assembly | low | done |
| IMP-043 | Live smoke: `sync universe` full listed + sample financials all-scope | med | open |
| IMP-044 | Streamlit credit/status use `list_tickers(scope=)` consistently | low | open |
