# Subagent playbook: Sync / data QA

## Goal

Verify Ibovespa lake coverage after sync; flag gaps without re-architecting collectors.

## Before exploring

Read `README.md`, `docs/aar/INDEX.md`, and the latest `docs/aar/automation/*.md`.

## Procedure

1. Prefer `.\.venv\Scripts\python.exe scripts/sync_pilot.py --dry-run` to see plan, or run real sync with `--skip-transcripts` if RI crawl is too slow.
2. Run coverage:

```bash
.\.venv\Scripts\python.exe -m decifra status
```

3. Spot-check tickers with known good history: **PETR4**, **VALE3**, **ITUB4** (financial CSVs + notices + transcripts indexes).
4. Flag:
   - Missing CNPJ in `meta.json`
   - Missing income/balance/cash (known: **ASAI3**)
   - Missing `prices.csv` (treat as regression after IMP-001 backfill)
5. Prefer `sync_pilot` so AAR + dashboard refresh happen together; otherwise write an AAR and run `scripts/update_session_dashboard.py`.
6. Log lasting automation meta-gaps in `docs/improvements/AUTOMATION.md`.

## Do not

- Assume global `decifra` on PATH
- Treat this as bureau credit or Open Finance data
- Launch a full codebase explore if AARs already explain the store layout
- Skip dashboard refresh after a collection/automation run
