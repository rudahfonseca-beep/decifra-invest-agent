# Unified Financial Data Pipeline — Implementation Roadmap

**Target:** Full end-state architecture bridging equity and credit (see [gap analysis](unified-pipeline-gap-analysis.md)).  
**This doc:** Sequenced deliverables for follow-on implementation sessions. Docs/skills/rules for the toolkit are already installed.

---

## Phase overview

| Phase | Focus | Key deliverables |
|-------|--------|------------------|
| **1** | Primary ingestion | CVM FRE; ANBIMA FI; B3 shares/mcap + Balcão bonds; CLI sync stages |
| **2** | Entity resolution & fallbacks | CNPJ↔CVM↔ticker↔ISIN; Hierarchy of Truth; private-issuer fallback |
| **3** | Valuation & credit modeling | APV; Merton/DtD; debt capacity flags; OCF→FCFE waterfall |
| **4** | Fund exposure | CVM INF_DIARIO + CDA; SEC EDGAR |
| **5** | Standardization & UI | Three schemas + lineage; ITR–debt alignment; React dark-mode UI |

Keep existing FCFF/WACC DCF, peer credit scores, and Streamlit as complementary paths until Phase 5 cutover criteria are met.

---

## Phase 1 — Primary ingestion engine

### Deliverables

| Item | Package / lake | Acceptance |
|------|----------------|------------|
| FRE zip download + key extracts | `src/decifra/cvm/fre.py` → `data/cache/cvm/` + company extracts | Idempotent sync; documented account/field map |
| ANBIMA debentures / CRI / CRA | `src/decifra/anbima/` → `data/cache/anbima/` + `data/companies/{id}/debt/` | Yields, indexers (CDI/IPCA+), covenants best-effort |
| B3 official shares / mcap | `src/decifra/b3/` or extend `universe/` | Synced artifact preferred over yfinance-only |
| B3 Balcão bond registrations | same | Linked by CNPJ/ISIN when available |
| CLI | `decifra sync fre\|anbima\|b3-bonds` | Wired into `sync_pilot` stages when stable |

### IMP refs

`IMP-020` (FRE), `IMP-021` (ANBIMA), `IMP-022` (B3 shares/Balcão).

---

## Phase 2 — Entity resolution & fallbacks

### Deliverables

| Item | Target | Acceptance |
|------|--------|------------|
| Mapping dictionary | `src/decifra/entities/` + `data/universe/entities.json` | Resolve CNPJ ↔ CVM code ↔ B3 ticker ↔ ISIN |
| Hierarchy of Truth | `entities/resolve.py` | Conflicts resolve: CVM > ANBIMA > Rating Agency > Web screeners |
| Private issuer fallback | CLI + [`docs/workflows/private-issuer-fallback.md`](../workflows/private-issuer-fallback.md) | No Cat. A → ANBIMA prospectus → Balcão → rating PDFs |

Consumers (`credit/`, `valuation/`, reports) must call the resolver instead of ad hoc meta joins.

### IMP refs

`IMP-023` (entity graph), `IMP-024` (hierarchy + private fallback).

---

## Phase 3 — Valuation & credit modeling

### Deliverables

| Item | Module | Formula / rule |
|------|--------|----------------|
| APV | `src/decifra/valuation/apv.py` | \(V_L = V_U + \mathrm{PV}(\text{Tax Shield}) - \mathrm{PV}(\text{Distress Costs})\) |
| Merton / DtD | `src/decifra/credit/merton.py` | Equity = Call\((V, D, r, T, \sigma_V)\); Distance to Default |
| Debt capacity | `src/decifra/credit/capacity.py` | Flag breaches: Net Debt/EBITDA ≤ 3.5x; DSCR ≥ 1.25x |
| Cash flow waterfall | `src/decifra/valuation/waterfall.py` | OCF → mandatory amortization/interest → residual FCFE |

Do not remove `valuation/dcf.py` or peer `credit/scoring.py`.

### IMP refs

`IMP-025` (APV), `IMP-026` (Merton), `IMP-027` (capacity), `IMP-028` (waterfall/FCFE).

---

## Phase 4 — Fund exposure

### Deliverables

| Item | Target | Acceptance |
|------|--------|------------|
| CVM INF_DIARIO | `src/decifra/funds/cvm.py` → `data/funds/` | Daily NAV/AUM cache |
| CVM CDA | same | Monthly line-by-line holdings |
| SEC EDGAR | `src/decifra/funds/edgar.py` | ADR/foreign exposure where relevant |
| Daily workflow | [`docs/workflows/daily-market-fund-sync.md`](../workflows/daily-market-fund-sync.md) | Runner + AUTO tracking |

### IMP refs

`IMP-029` (CVM funds), `IMP-030` (EDGAR).

---

## Phase 5 — Data standardization & UI

### Deliverables

| Item | Target | Acceptance |
|------|--------|------------|
| Company Profile schema | `src/decifra/schemas/` + `docs/schemas/` | Stable JSON contract |
| Integrated Credit & Debt Matrix | same | Facilities, maturities, covenants, capacity headroom |
| Valuation Waterfall Analysis | same | APV and/or OCF→FCFE bridge with disclosed inputs |
| Lineage on every metric | schema field e.g. `lineage.source_doc` | Points to origin document (e.g. CVM DFP Note) |
| ITR–debt date alignment | credit/valuation readers | Align `DT_REFER` across statements and debt schedules |
| React dark-mode UI | `frontend/` (or `apps/research-ui/`) | Consumes lake/API; Streamlit remains until cutover |

### IMP refs

`IMP-031` (three schemas + lineage), `IMP-032` (ITR–debt alignment), `IMP-033` (React UI).

---

## Automation (cross-cutting)

| Workflow | Doc | AUTO |
|----------|-----|------|
| Daily market & fund sync | [daily-market-fund-sync.md](../workflows/daily-market-fund-sync.md) | `AUTO-008` |
| Quarterly earnings trigger | [quarterly-earnings-trigger.md](../workflows/quarterly-earnings-trigger.md) | `AUTO-009` |
| Private issuer fallback | [private-issuer-fallback.md](../workflows/private-issuer-fallback.md) | `AUTO-010` |

Operational rules: [`.cursor/rules/unified-pipeline.mdc`](../../.cursor/rules/unified-pipeline.mdc).

---

## Suggested session order

1. Phase 1 FRE + ANBIMA (largest data unlock)  
2. Phase 2 entity graph (unblocks multi-source joins)  
3. Phase 3 capacity + waterfall (fast wins on existing CVM data), then APV/Merton  
4. Phase 4 funds  
5. Phase 5 schemas → React  

Re-run the [pipeline auditor](../prompts/unified-pipeline-auditor.md) after each phase and update the [gap analysis](unified-pipeline-gap-analysis.md).
