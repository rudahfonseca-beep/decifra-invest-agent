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

Automate existing decifra-invest-agent data collection (`decifra sync`) for stages: **universe**.
Capture before/after coverage, write this automation AAR, and **refresh the human HTML dashboard** (required closeout).
Universe: full Ibovespa set.
Dry-run: **True**.

## 2. What actually happened

Ran `scripts/sync_pilot.py` at 2026-07-31 22:29 UTC.

### Stages

- `universe`: OK — `F:\Archive\Dev\python\DecifraCR\.venv\Scripts\python.exe -m decifra sync universe`

### Coverage before

- tickers: 78
- financials: 78/78
- prices: 78/78
- notices: 78/78
- transcripts: 78/78
- notice_pdfs: 755
- transcript_files: 295
- missing_financials: (none)
- missing_prices_count: 0


### Coverage after

- tickers: 78
- financials: 78/78
- prices: 78/78
- notices: 78/78
- transcripts: 78/78
- notice_pdfs: 755
- transcript_files: 295
- missing_financials: (none)
- missing_prices_count: 0


### Machine-readable summary

```json
{
  "before": {
    "tickers": 78,
    "financials": "78/78",
    "prices": "78/78",
    "notices": "78/78",
    "transcripts": "78/78",
    "missing_financials": [],
    "missing_prices_count": 0,
    "notice_pdfs": 755,
    "transcript_files": 295
  },
  "after": {
    "tickers": 78,
    "financials": "78/78",
    "prices": "78/78",
    "notices": "78/78",
    "transcripts": "78/78",
    "missing_financials": [],
    "missing_prices_count": 0,
    "notice_pdfs": 755,
    "transcript_files": 295
  },
  "stages": [
    "universe"
  ],
  "dry_run": true
}
```

## 3. Gaps

- Dry-run only — no network sync executed.

## 4. Lessons

- Idempotent CVM ZIP cache makes re-sync safe; status delta is the audit trail.
- Prefer `scripts/sync_pilot.py` over ad-hoc sync so every collection run leaves an AAR **and** refreshes the dashboard.
- Transcripts/RI crawl is the slowest stage — use `--skip-transcripts` for refresh loops.
- Product/data gaps: [`docs/improvements/LOG.md`](../../improvements/LOG.md). Automation meta: [`docs/improvements/AUTOMATION.md`](../../improvements/AUTOMATION.md).

## 5. Improvements

### Product / data

See open `IMP-*` rows in [`docs/improvements/LOG.md`](../../improvements/LOG.md) (do not hardcode stale status here).

### Automation opportunities

| ID | Opportunity | Priority | Status |
|----|-------------|----------|--------|
| AUTO-001 | Cursor Automation wrapping this runner (IMP-008) | low | open |
| AUTO-003 | Prefer sync_pilot over ad-hoc `decifra sync` | med | open |
| (run) | Dry-run — no lake mutation; dashboard still refreshed for AAR visibility | low | note |

Track lasting meta-follow-ups in [`docs/improvements/AUTOMATION.md`](../../improvements/AUTOMATION.md).
