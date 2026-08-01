---
id: 2026-08-01-ui-one-command
date: 2026-08-01
title: Fix DecifraCR leftovers + one-command React UI
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Fix DecifraCR leftovers + one-command React UI

## 1. Plan / purpose / objective

Close leftover `DecifraCR` path debt (broken editable venv + living docs still treating IMP-013 as open), then add Streamlit-parity `decifra ui` that ensures frontend npm deps and starts lake API + Vite together.

## 2. What actually happened

- Recreated `.venv` under `decifra-invest-agent` and reinstalled `pip install -e ".[dev]"` so launchers no longer point at `DecifraCR`.
- Closed **IMP-013** in `docs/improvements/LOG.md`; updated FUTURE_AGENTS, backlog/rename AAR notes, README install snippet; refreshed session dashboard.
- Added `decifra ui` (`--port`, `--api-port`, `--skip-install`, `--no-api`) in `src/decifra/cli.py`.
- Added `scripts/dev_ui.ps1`; documented one-liner in README + `frontend/README.md`; updated cutover gate 9.
- Smoke: `decifra ui --no-api --skip-install --port 5199` reached Vite ready.

## 3. Gaps

- Historical automation AAR command transcripts still record absolute `DecifraCR` paths (left as factual run records).
- Full live smoke with lake API + browser not run this session (Node/`--no-api` path verified).

## 4. Lessons

- After a folder rename, Windows venv scripts keep the old interpreter path until the venv is recreated — docs-only renames do not fix `pip`/`decifra` launchers.
- Analyst DX for React should mirror `decifra dashboard`: one command that owns the process tree (API child + Vite foreground).

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-013 | Rename folder + re-run editable install | med | done |
