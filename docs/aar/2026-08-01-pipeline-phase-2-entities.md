---
id: 2026-08-01-pipeline-phase-2-entities
date: 2026-08-01
title: Pipeline Phase 2 — Entity resolution & fallbacks
session_type: agent
transcript_id: ""
status: completed
---

# AAR: Pipeline Phase 2 — Entity resolution & fallbacks

## 1. Plan / purpose / objective

Implement IMP-023/024: canonical entity graph (CNPJ↔CVM↔ticker↔ISIN), Hierarchy of Truth, private-issuer fallback CLI/workflow, and cheap consumer hook via `load_identity`.

## 2. What actually happened

- Added `src/decifra/entities/resolve.py` with hierarchy, conflict resolution, universe build, resolve, private-issuer fallback.
- CLI: `decifra entities sync|resolve|private-issuer`.
- `store.folders.load_identity` enriches meta with ISINs/entity tickers.
- Workflow doc updated from stub to implemented CLI.
- Smoke: built 76 entities into `data/universe/entities.json` (gitignored lake).
- Tests: `tests/test_entities.py` (2 passed).

## 3. Gaps

- Rating-agency step in private-issuer chain is still a stub.
- Consumers (credit/valuation/report) not fully migrated off ad-hoc meta joins — only `load_identity` helper added.
- ISIN coverage depends on Phase 1 debt extracts being present per ticker.

## 4. Lessons

- Seed entities from existing Ibovespa meta first; debt ISINs are additive.
- Keep Hierarchy of Truth as a shared constant consumed by conflict helpers and docs.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-023 | Entity graph | high | done |
| IMP-024 | Hierarchy + private fallback | high | done |
| IMP-035 | Migrate credit/valuation joins to `load_identity` / resolver | med | open |
