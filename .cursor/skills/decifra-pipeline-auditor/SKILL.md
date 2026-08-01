---
name: decifra-pipeline-auditor
description: >-
  Audit decifra-invest-agent against the Unified Financial Data Pipeline
  (four pillars: ingestion, entity resolution, modeling, output schemas).
  Use for gap analysis, architecture reviews, or remediation planning.
---

# Unified pipeline auditor

## When

User asks for a pipeline gap analysis, architecture audit, pillar Pass/Fail, or remediation vs the Unified Financial Data Pipeline target.

## Docs first

1. Read `README.md`
2. Read `docs/architecture/unified-pipeline-gap-analysis.md` and `docs/architecture/unified-pipeline-roadmap.md`
3. Skim `docs/improvements/LOG.md` / `AUTOMATION.md` for open `IMP-*` / `AUTO-*`
4. Only then explore `src/decifra/` for evidence

Full system prompt: `docs/prompts/unified-pipeline-auditor.md`.

## Four pillars (must grade Pass/Fail)

### Pillar 1 — Multi-source ingestion

| Layer | Required | Evidence today (typical) |
|-------|----------|---------------------------|
| 1 Regulatory | CVM DFP, ITR, **FRE** — BS, IS, CF | `src/decifra/cvm/financials.py` (DFP/ITR); FRE often missing |
| 2 Fixed income | ANBIMA debentures / CRI / CRA | `src/decifra/anbima/` if present |
| 3 Equities & OTC | B3 shares, mcap, Balcão bonds | `universe/`, `b3/`, `valuation/market_data.py` |
| 4 Private issuers | Rating agency Adjusted ND / EBITDA | scrapers under ratings/ if present |
| 5 Funds | CVM INF_DIARIO + CDA; SEC EDGAR | `src/decifra/funds/` if present |

### Pillar 2 — Entity resolution & fallbacks

- Map CNPJ ↔ CVM code ↔ B3 ticker ↔ ISIN
- Hierarchy of Truth: **CVM Open Data > ANBIMA > Rating Agency > Web screeners**
- Private issuer fallback: no Cat. A → ANBIMA prospectus → B3 Balcão → rating releases

### Pillar 3 — Modeling fidelity

- APV: \(V_L = V_U + \mathrm{PV}(TS) - \mathrm{PV}(FDC)\)
- Merton: equity as European call; Distance to Default
- Capacity: Net Debt/EBITDA ≤ 3.5x; DSCR ≥ 1.25x flags
- Waterfall: OCF → mandatory debt service → FCFE  
Also note existing FCFF/WACC DCF and peer credit as complementary (not substitutes for APV/Merton).

### Pillar 4 — Output schema & validation

- Three tables: Company Profile; Integrated Credit & Debt Matrix; Valuation Waterfall
- Currency BRL (or USD) normalization; ITR dates aligned with debt schedules
- Per-metric lineage tags to origin documents
- UI: React target vs Streamlit interim

## Output format

1. **Executive Summary** — Pass/Fail per pillar and overall
2. **Missing Components** — bullets (databases, formulas, schemas)
3. **Code Corrections** — Python snippets or concrete module patches for gaps (or targets if not yet implementable)
4. Update `docs/architecture/unified-pipeline-gap-analysis.md` when findings change material status
5. Append new follow-ups to `docs/improvements/LOG.md` (`IMP-*`) and/or `AUTOMATION.md` (`AUTO-*`)

## Rules

- Do not claim ANBIMA/FRE/React exist unless code + lake artifacts prove it
- Prefer `.venv\Scripts\python.exe` for any smoke commands
- Do not invent SQL stores — lake is filesystem (`data/companies/`, `data/cache/`, `data/universe/`, future `data/funds/`)
