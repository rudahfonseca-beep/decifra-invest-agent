---
id: 2026-07-20-greenfield-pipeline
date: 2026-07-20
title: Greenfield Ibovespa pipeline
session_type: agent
transcript_id: 667ce9cd-9513-44c0-909d-1ec52cf44f22
status: completed
---

# AAR: Greenfield Ibovespa pipeline

## 1. Plan / purpose / objective

Build a fully operational B3 financial research assistant: per-company folders, public IR/CVM data, historical financial CSVs, notices, and call materials. Scope narrowed to **Ibovespa + data pipeline + CLI** (not full B3, not a web UI).

## 2. What actually happened

- Created package `decifra` 0.1.0 with CLI (`sync universe|financials|notices|transcripts|all`, `status`, `ask`).
- Per-ticker store under `data/companies/{TICKER}/` with `meta.json`, financials, notices, transcripts.
- Sources: B3 portfolio + CNPJ enrichment, CVM DFP/ITR/IPE, yfinance/brapi prices, best-effort RI crawl.
- Synced ~78 Ibovespa tickers; financial CSVs for 77/78; notices and transcript indexes for all.
- Added unit tests for universe/financials parsing.

## 3. Gaps

- Wrong PETR4 CNPJ match early on (later improved via B3 enrichment).
- ASAI3 still missing DFP/ITR financial CSVs.
- Prices present for only a handful of tickers.
- Original “crawl all IR pages” goal reduced to CVM/official feeds + light RI harvest.
- IPE column-name mismatches and notices CNPJ filter bugs during development.
- No durable session documentation at the time.

## 4. Lessons

- Prefer official CVM/B3 feeds over brittle full-site IR crawls for v1.
- CNPJ↔ticker mapping is the critical join key; validate early with PETR4/VALE3.
- Idempotent ZIP cache under `data/cache/cvm/` makes re-runs feasible.
- Always use project `.venv` on Windows — global install PATH is unreliable.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-001 | Backfill prices for all tickers | high | open |
| IMP-002 | ASAI3 financials diagnosis | high | open |
| IMP-003 | Expand CVM cache year coverage | med | open |
