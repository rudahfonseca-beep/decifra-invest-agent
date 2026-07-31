---
id: 2026-07-20-credit-dashboard
date: 2026-07-20
title: Creditworthiness Streamlit dashboard
session_type: agent
transcript_id: 91420427-05ef-4794-8d96-239e03be0d1e
status: completed
---

# AAR: Creditworthiness Streamlit dashboard

## 1. Plan / purpose / objective

Add a dashboard to identify creditworthiness by industry using the gathered CVM/B3 lake — fundamental ratios plus notice/transcript signals. Local Streamlit (not bureau/Open Finance).

## 2. What actually happened

- Implemented `credit/metrics`, `credit/scoring`, `credit/signals`.
- Streamlit app at `dashboard/app.py`; CLI `decifra credit` and `decifra dashboard`.
- Bank/insurer vs non-financial scorecards; peer percentiles; keyword risk penalty (cap 15).
- Expanded tests (~12); Energy ranking smoke (e.g. AXIA3→AURE3 path).
- Clarified product is **research-grade peer scoring**, not Serasa/bureau credit.

## 3. Gaps

- Empty interest coverage for PETR4 (account-mapping / label aliases).
- `pip install` sometimes landed `decifra` outside PATH (Windows user Scripts).
- Sparse or inconsistent sector strings affect industry cohorts.

## 4. Lessons

- Separate financial vs non-financial scorecards early.
- Qualitative keyword penalties need a hard cap so they do not dominate fundamentals.
- Install and invoke via `.\.venv\Scripts\python.exe -m decifra` to avoid PATH churn.
- Re-exploring the whole codebase every session wastes time — need AAR memory.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-004 | Fix PETR4 interest coverage + regression test | high | open |
| IMP-005 | Codify Windows venv PATH rule | med | open → addressed in rules |
| IMP-007 | Normalize free-text sectors | med | open |
