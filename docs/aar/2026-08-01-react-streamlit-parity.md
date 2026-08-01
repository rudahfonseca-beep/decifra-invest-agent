---
id: 2026-08-01-react-streamlit-parity
date: 2026-08-01
title: React Streamlit parity — industries, tickers, research views
session_type: agent
transcript_id: ""
status: completed
---

# AAR: React Streamlit parity

## 1. Plan / purpose / objective

Add industry list + ticker list UIs and port Streamlit dashboard functionality into the Terminal Dark React shell.

## 2. What actually happened

- Extended lake API (`schemas/research_api.py` + `api_server.py`): `/api/credit`, `/api/industries`, `/api/tickers`, `/api/coverage`, `/api/valuation/*`, `/api/report/*` (POST build).
- React views: Industries, Tickers, Credit overview, Company detail, Valuation, Report builder, Coverage — plus existing screener/schema panes.
- Sidebar/filter bar; sample fixtures exported (`credit_table`, `industries`, `tickers`, `coverage`).
- `npm run build` and research API smoke tests green.

## 3. Gaps

- Report HTML generation still needs OPENAI_API_KEY on the API process.
- Sensitivity heatmap is table-only (no Plotly).
- Offline sample fallback for `/api/credit/{ticker}` detail is API-only.

## 4. Lessons

- Serialize credit DataFrames once behind a small API cache so React filters stay responsive.
- Keep Streamlit until cutover checklist gates pass (`docs/workflows/streamlit-react-cutover.md`).

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-039 | Cutover gates still apply before retiring Streamlit | low | open checklist |
