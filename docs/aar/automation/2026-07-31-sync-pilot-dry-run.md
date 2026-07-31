---
id: 2026-07-31-sync-pilot-dry-run
date: 2026-07-31
title: Sync pilot (dry-run)
session_type: automation
transcript_id: ""
status: completed
---

# AAR: Sync pilot (dry-run)

## 1. Plan / purpose / objective

Automate existing DecifraCR data collection (`decifra sync`) for stages: **universe, financials, notices, transcripts**.
Capture before/after coverage, write this automation AAR, and refresh the human HTML dashboard.
Universe: full Ibovespa set.
Dry-run: **True**.

## 2. What actually happened

Ran `scripts/sync_pilot.py` at 2026-07-31 16:44 UTC.

### Stages

- `universe`: OK — `F:\Archive\Dev\python\DecifraCR\.venv\Scripts\python.exe -m decifra sync universe`
- `financials`: OK — `F:\Archive\Dev\python\DecifraCR\.venv\Scripts\python.exe -m decifra sync financials`
- `notices`: OK — `F:\Archive\Dev\python\DecifraCR\.venv\Scripts\python.exe -m decifra sync notices`
- `transcripts`: OK — `F:\Archive\Dev\python\DecifraCR\.venv\Scripts\python.exe -m decifra sync transcripts`

### Coverage before

- tickers: 78
- financials: 77/78
- prices: 3/78
- notices: 78/78
- transcripts: 78/78
- notice_pdfs: 392
- transcript_files: 295
- missing_financials: ASAI3
- missing_prices_count: 75


### Coverage after

- tickers: 78
- financials: 77/78
- prices: 3/78
- notices: 78/78
- transcripts: 78/78
- notice_pdfs: 392
- transcript_files: 295
- missing_financials: ASAI3
- missing_prices_count: 75


### Machine-readable summary

```json
{
  "before": {
    "tickers": 78,
    "financials": "77/78",
    "prices": "3/78",
    "notices": "78/78",
    "transcripts": "78/78",
    "missing_financials": [
      "ASAI3"
    ],
    "missing_prices_count": 75,
    "notice_pdfs": 392,
    "transcript_files": 295
  },
  "after": {
    "tickers": 78,
    "financials": "77/78",
    "prices": "3/78",
    "notices": "78/78",
    "transcripts": "78/78",
    "missing_financials": [
      "ASAI3"
    ],
    "missing_prices_count": 75,
    "notice_pdfs": 392,
    "transcript_files": 295
  },
  "stages": [
    "universe",
    "financials",
    "notices",
    "transcripts"
  ],
  "dry_run": true
}
```

## 3. Gaps

- Dry-run only — no network sync executed.
- Missing full financial CSVs: ASAI3 (IMP-002).
- 75 tickers still missing prices.csv (IMP-001).

## 4. Lessons

- Idempotent CVM ZIP cache makes re-sync safe; status delta is the audit trail.
- Prefer `scripts/sync_pilot.py` over ad-hoc sync so every collection run leaves an AAR.
- Transcripts/RI crawl is the slowest stage — use `--skip-transcripts` for refresh loops.
- Known lake gaps (ASAI3 financials, sparse prices) persist across successful syncs until specifically fixed.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-001 | Backfill prices.csv for remaining tickers | high | open |
| IMP-002 | Resolve ASAI3 / missing financials | high | open |
| IMP-008 | Optional Cursor Automation wrapping this runner | low | open |

See [`docs/improvements/LOG.md`](../../improvements/LOG.md).
