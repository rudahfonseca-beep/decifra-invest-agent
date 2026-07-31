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
   - Missing `prices.csv` (most tickers)
5. Write or update an automation/agent AAR; run `scripts/update_session_dashboard.py`.

## Do not

- Assume global `decifra` on PATH
- Treat this as bureau credit or Open Finance data
- Launch a full codebase explore if AARs already explain the store layout
