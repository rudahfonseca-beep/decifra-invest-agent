---
id: 2026-08-01-backlog-imp-closeout
date: 2026-08-01
title: Close open IMP backlog (034–039, 003, 008, 015–018)
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Close open IMP backlog

## 1. Plan / purpose / objective

Implement the open improvements listed on the session dashboard: pipeline/UI (IMP-034..039), valuation UX (015–018), CVM cache (003), Cursor Automation (008), and note folder rename (013) / valuation PR (017).

## 2. What actually happened

- **IMP-036/038:** `assemble_apv`, `assemble_merton`, `assemble_capacity`, `schemas/screener.py`; CLI `--ticker` on apv/merton/capacity; `schemas screener|export-ui`.
- **IMP-037:** stdlib lake API (`schemas serve`) + Vite `/api` proxy + React fetch fallback to samples.
- **IMP-039:** `docs/workflows/streamlit-react-cutover.md` parity checklist.
- **IMP-035:** credit/valuation/report use `load_identity`; store package exports it.
- **IMP-034:** B3 `GetListedSupplementCompany` wired; `sync b3-shares --network` (PETR4 → 12.8B shares).
- **IMP-015/016/018:** shares fallback chain; extreme upside callout; `@st.cache_data` on sensitivity grid.
- **IMP-003:** DFP/ITR 2020–21 already present; IPE 2020–22 warmed; `DEFAULT_NOTICE_YEARS` starts at 2020.
- **IMP-008 / AUTO-001:** Automations editor opened with sync_pilot draft + workflow doc.
- **IMP-017:** Confirmed PR #6 had been opened; Valuation tab already on `main`.
- Tests: assemble/B3/extreme-upside + updated credit patches green.

## 3. Gaps

- **IMP-013** still open — cannot rename `DecifraCR` while Cursor has the workspace open.
- Cursor Automation must be **saved** by the user in the Automations editor (draft only until then).
- Dedicated `fato_relevante_*.csv` files were not observed in cache; notices path used IPE zips for 2020–22.
- B3 supplement does not return market cap (shares only); mcap still from yfinance/implied.

## 4. Lessons

- B3 `GetDetail` is identity-only; share counts require `GetListedSupplementCompany` + `issuingCompany`.
- Screener/API should assemble from engines against the lake before polishing UI fixtures.
- Patch tests at the consumer import (`load_identity`) when swapping identity helpers.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-013 | Rename local folder after closing Cursor | med | open |
| AUTO-001 | User saves Automation draft in editor | low | open→done draft; confirm save |
