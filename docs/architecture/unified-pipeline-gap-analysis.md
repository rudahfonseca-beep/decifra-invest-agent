# Unified Financial Data Pipeline — Gap Analysis

**Date:** 2026-08-01 (re-audit after Phases 1–5 implementation)  
**Grade:** **PARTIAL PASS** — core pillars 2–4 ship research-grade modules; Pillar 1 still missing rating-agency parsers and full live Balcão/FRE coverage.  
**Scope:** Full end-state architecture (equity + credit + fixed income + funds).  

Related: [unified-pipeline-roadmap.md](unified-pipeline-roadmap.md) · [pipeline-progress.json](pipeline-progress.json) · auditor prompt [`docs/prompts/unified-pipeline-auditor.md`](../prompts/unified-pipeline-auditor.md)

---

## 1. Executive Summary

| Pillar | Grade | Verdict |
|--------|-------|---------|
| 1 Multi-source ingestion | **Fail** | DFP/ITR + FRE/ANBIMA/B3/funds/EDGAR modules exist; **rating agency parsers** still missing; FRE/ANBIMA/Balcão often fixture/cache-backed |
| 2 Entity resolution & fallbacks | **Pass** | `entities/` + `entities.json`; Hierarchy of Truth; private-issuer fallback CLI (rating step stub) |
| 3 Integrated modeling | **Pass** | FCFF/WACC + peer credit kept; APV, Merton/DtD, capacity, OCF→FCFE waterfall added |
| 4 Output schema & validation | **Pass** | Three schemas + lineage assemblers; ITR–debt alignment; React dark MVP; Streamlit interim |

**Pipeline overall: PARTIAL PASS** — roadmap Phases 1–5 code landed on `feat/unified-pipeline`; do not claim production-grade live ANBIMA/Balcão/rating coverage until lake sync is proven at scale.

---

## 2. Missing Components (remaining)

### Pillar 1 — Ingestion

- Credit rating agency parsers (Fitch / Moody's / S&P) for Adjusted Net Debt / Adjusted EBITDA
- Hardened live FRE year coverage across universe (cache warm-up)
- Official B3 shares-outstanding network detail API (IMP-034)
- Production ANBIMA feed (beyond cache/fixture CSV)

### Pillar 2 — Entity resolution

- Full migration of credit/valuation/report joins to `load_identity` (IMP-035)
- Rating-agency step in private-issuer chain (still stub)

### Pillar 3 — Modeling

- Auto-assemble APV/Merton inputs from CVM + market for a ticker (IMP-036)

### Pillar 4 — Outputs / UI

- Live lake/API feed for React UI (IMP-037)
- Automated Streamlit → React cutover gates

---

## 3. What Exists (evidence paths)

### Pillar 1

| Capability | Path |
|------------|------|
| CVM DFP/ITR | `src/decifra/cvm/financials.py` |
| CVM FRE | `src/decifra/cvm/fre.py` · `decifra sync fre` |
| ANBIMA debt | `src/decifra/anbima/` · `decifra sync anbima` |
| B3 shares / Balcão | `src/decifra/b3/` · `decifra sync b3-shares\|b3-bonds` |
| CVM Funds + EDGAR | `src/decifra/funds/` · `decifra sync funds\|edgar` |

### Pillar 2

| Capability | Path |
|------------|------|
| Entity graph | `src/decifra/entities/resolve.py` · `data/universe/entities.json` |
| Hierarchy of Truth | `HIERARCHY_OF_TRUTH` in `entities/resolve.py` |
| Private issuer fallback | `decifra entities private-issuer` · workflow doc |
| Identity hook | `store.folders.load_identity` |

### Pillar 3

| Capability | Path |
|------------|------|
| FCFF/WACC DCF | `valuation/dcf.py` (kept) |
| Peer credit | `credit/scoring.py` (kept) |
| APV | `valuation/apv.py` |
| Merton / DtD | `credit/merton.py` |
| Capacity | `credit/capacity.py` |
| OCF→FCFE waterfall | `valuation/waterfall.py` |

### Pillar 4

| Capability | Path |
|------------|------|
| Schemas | `docs/schemas/` · `src/decifra/schemas/` |
| ITR–debt alignment | `schemas/alignment.py` |
| React dark MVP | `frontend/` |
| Streamlit interim | `src/decifra/dashboard/app.py` |
| Pipeline monitor | HTML dashboard **Pipeline** tab · `pipeline-progress.json` |

---

## 4. Phase AARs

| Phase | AAR |
|-------|-----|
| 1 | [2026-08-01-pipeline-phase-1-ingestion.md](../aar/2026-08-01-pipeline-phase-1-ingestion.md) |
| 2 | [2026-08-01-pipeline-phase-2-entities.md](../aar/2026-08-01-pipeline-phase-2-entities.md) |
| 3 | [2026-08-01-pipeline-phase-3-modeling.md](../aar/2026-08-01-pipeline-phase-3-modeling.md) |
| 4 | [2026-08-01-pipeline-phase-4-funds.md](../aar/2026-08-01-pipeline-phase-4-funds.md) |
| 5 | [2026-08-01-pipeline-phase-5-schemas-ui.md](../aar/2026-08-01-pipeline-phase-5-schemas-ui.md) |

---

## 5. Improvement IDs (open follow-ups)

See [`docs/improvements/LOG.md`](../improvements/LOG.md): IMP-034..037 and remaining non-pipeline IMPs. Automation: AUTO-008..010 still open for Cursor Automation wraps.
