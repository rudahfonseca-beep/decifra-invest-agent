---
id: 2026-08-01-pipeline-phase-3-modeling
date: 2026-08-01
title: Pipeline Phase 3 — APV, Merton, capacity, waterfall
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Pipeline Phase 3 — Valuation & credit modeling

## 1. Plan / purpose / objective

Ship IMP-025..028 complementary engines without removing FCFF/WACC DCF or peer credit scores: APV, Merton/DtD, debt capacity flags, OCF→FCFE waterfall.

## 2. What actually happened

- Added `valuation/apv.py`, `valuation/waterfall.py`, `credit/merton.py`, `credit/capacity.py`.
- CLI: `decifra valuation apv|waterfall`, `decifra merton`, `decifra capacity`.
- Tests: `tests/test_pipeline_phase3.py`.
- Existing `dcf.py` / `scoring.py` untouched.

## 3. Gaps

- Engines are formula-first; not yet auto-wired to lake statement extractors for one-command ticker APV/Merton.
- Merton uses asset-vol input (no equity-vol inversion solver yet).

## 4. Lessons

- Keep new engines complementary — acceptance is coexistence with DCF/peer scores.
- Capacity thresholds (3.5x / 1.25x) belong in named constants for report/schema reuse.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-025..028 | APV / Merton / capacity / waterfall | med | done |
| IMP-036 | Auto-assemble APV/Merton inputs from CVM + market for a ticker | med | open |
