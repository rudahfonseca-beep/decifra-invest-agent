---
id: 2026-07-31-report-builder
date: 2026-07-31
title: Shared credit/equity report builder
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Shared credit/equity report builder

## 1. Plan / purpose / objective

Implement the planned shared report builder (delivery **C** + shared credit/equity mode): users select companies, industries, and KPIs; platform assembles local facts and packs an LLM prompt (optional interactive HTML).

## 2. What actually happened

- Added `src/decifra/report/` (`catalog`, `spec`, `assemble`, `prompt`, `html_scaffold`, `generate`).
- Extracted `assistant/llm.py`; wired `decifra report build` and Streamlit **Report builder** tab.
- Exposed `ebit_margin` in metrics/scoring for equity mode.
- Artifacts under `data/reports/{slug}/`; unit tests `tests/test_report_*.py` (all green).
- Smoke: CLI build for PETR4 + Energy + VALE3 comparative wrote prompt/context without API key.

## 3. Gaps

- HTML generation not smoke-tested in-session without confirming live `OPENAI_API_KEY`.
- No multi-user auth / saved report library (explicitly out of scope).
- Equity mode still fundamentals-only (no DCF / multiples).

## 4. Lessons

- Prompt-first deliverable unblocks users without API keys; HTML is an optional second step.
- Validate tickers/industries against local universe before assemble.
- Keep report assembly fact-only; narrative stays in the LLM layer.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-006 | Implement report builder (chosen mode) | high | done |
| IMP-011 | Document report workflow / skill / QA playbook | med | done (this session) |
| IMP-007 | Sector normalization (better peer cohorts) | med | open |
| IMP-012 | Optional offline HTML render from context (no LLM) | low | open |
