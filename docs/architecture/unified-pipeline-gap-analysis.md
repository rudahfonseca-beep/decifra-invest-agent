# Unified Financial Data Pipeline — Gap Analysis

**Date:** 2026-08-01  
**Grade:** **FAIL** against the ideal Unified Financial Data Pipeline  
**Scope:** Full end-state architecture (equity + credit + fixed income + funds).  
**Note:** Decifra today is a solid Ibovespa + CVM research lake with peer credit scores and FCFF/WACC valuation. That does not satisfy the four pillars below.

Related: [unified-pipeline-roadmap.md](unified-pipeline-roadmap.md) · auditor prompt [`docs/prompts/unified-pipeline-auditor.md`](../prompts/unified-pipeline-auditor.md) · skill [`.cursor/skills/decifra-pipeline-auditor/SKILL.md`](../../.cursor/skills/decifra-pipeline-auditor/SKILL.md)

---

## 1. Executive Summary

| Pillar | Grade | Verdict |
|--------|-------|---------|
| 1 Multi-source ingestion | **Fail** | Strong CVM DFP/ITR + B3 universe; missing FRE, ANBIMA, Balcão bonds, rating scrapers, funds/EDGAR |
| 2 Entity resolution & fallbacks | **Fail** | Heuristic ticker↔CNPJ↔CVM only; no ISIN, Hierarchy of Truth, or private-issuer fallback |
| 3 Integrated modeling | **Fail** | FCFF/WACC DCF + peer credit exist; APV, Merton/DtD, capacity covenants, FCFE waterfall missing |
| 4 Output schema & validation | **Fail** | Ad-hoc JSON/DataFrames + Streamlit; named schemas, full lineage, React UI missing |

**Pipeline overall: FAIL** — implement Phases 1–5 in the roadmap before claiming a unified equity/credit pipeline.

---

## 2. Missing Components

### Pillar 1 — Ingestion

- CVM **FRE** (Formulário de Referência) programmatic ingest
- **ANBIMA** debentures, CRI, CRA (yields, CDI/IPCA+ indexers, covenants)
- Official **B3** share counts / market cap sync (today: yfinance on demand)
- **B3 Balcão** private corporate bond registrations
- Credit rating agency parsers (Fitch / Moody's / S&P) for Adjusted Net Debt / Adjusted EBITDA
- CVM Funds **INF_DIARIO** (daily NAV) and **CDA** (monthly holdings)
- **SEC EDGAR** fund/issuer exposure where relevant

### Pillar 2 — Entity resolution

- ISIN mapping and reverse lookups
- Canonical entity store (`data/universe/entities.json` + `src/decifra/entities/`)
- Declared **Hierarchy of Truth**: CVM Open Data > ANBIMA > Rating Agency > Web screeners
- **Private issuer fallback**: no Cat. A filings → ANBIMA prospectus → B3 Balcão → rating releases

### Pillar 3 — Modeling

- **APV:** \(V_L = V_U + \mathrm{PV}(\text{Tax Shield}) - \mathrm{PV}(\text{Financial Distress Costs})\)
- **Merton** structural model / Distance to Default (equity as call on assets)
- Debt capacity flags: Net Debt/EBITDA ≤ 3.5x, DSCR ≥ 1.25x
- Cash flow waterfall: OCF → mandatory debt service → FCFE

### Pillar 4 — Outputs / UI

- Standardized tables: Company Profile, Integrated Credit & Debt Matrix, Valuation Waterfall
- Per-metric lineage tags (document-level provenance on every KPI)
- ITR reporting dates aligned with debt schedules (today credit/valuation prefer latest DFP only)
- React dark-mode investment UI (Streamlit remains interim research UI)

---

## 3. What Exists (evidence paths)

### Pillar 1 — partial

| Capability | Path |
|------------|------|
| CVM DFP/ITR BS / IS / CF | `src/decifra/cvm/financials.py`, `src/decifra/cvm/download.py`, `src/decifra/config.py` |
| Lake CSVs | `data/companies/{TICKER}/financials/{income_statement,balance_sheet,cash_flow}.csv` |
| Row tags | `SOURCE_DOC` (`DFP`/`ITR`), `SOURCE_YEAR` |
| IPE / fatos relevantes | `src/decifra/cvm/notices.py` |
| B3 Ibovespa + CNPJ | `src/decifra/universe/ibovespa.py`, `src/decifra/universe/b3_cnpj.py` |
| Prices / market snapshot | brapi → yfinance in financials sync; `src/decifra/valuation/market_data.py` |
| RI transcripts | `src/decifra/ri/` |

### Pillar 2 — partial

| Capability | Path |
|------------|------|
| Per-ticker identity | `data/companies/{TICKER}/meta.json` via `src/decifra/store/folders.py` |
| Fields | `ticker`, `cnpj`, `cvm_code`, company name, sector, `source: "ibovespa"` |
| Join for statements | CNPJ filter (+ name/stem heuristics) in `cvm/financials.py` |

Ad hoc precedence (not product policy): B3 listed CNPJ ≫ cadastro name ≫ DFP stem; consol ≫ individual; DFP ≫ ITR for annual KPIs.

### Pillar 3 — partial

| Capability | Path |
|------------|------|
| FCFF / WACC DCF | `src/decifra/valuation/dcf.py`, `assumptions.py`, `historical.py` |
| Trading multiples | `src/decifra/valuation/multiples.py` |
| Peer credit score | `src/decifra/credit/metrics.py`, `scoring.py`, `signals.py` |
| Related ratios | interest coverage, `ocf_to_net_debt`, leverage-ish peers — **not** 3.5x / DSCR gates |

### Pillar 4 — partial

| Capability | Path |
|------------|------|
| Report / valuation context JSON | `src/decifra/report/assemble.py`, `src/decifra/valuation/assemble.py` |
| Streamlit UI | `src/decifra/dashboard/app.py` |
| BRL scale for valuation | `valuation/historical.py` (`ESCALA_MOEDA` → absolute R$) |
| Light lineage | `SOURCE_DOC` / `SOURCE_YEAR`; valuation `methodology[]` notes — not per-metric audit tags |

---

## 4. Code Corrections (targets, not shipped here)

This audit slice installs docs/skills/rules only. Recommended module targets for follow-on sessions (see roadmap):

```text
src/decifra/cvm/fre.py
src/decifra/anbima/
src/decifra/b3/                    # shares/mcap + Balcão
src/decifra/entities/              # CNPJ↔CVM↔ticker↔ISIN + Hierarchy
src/decifra/valuation/apv.py
src/decifra/valuation/waterfall.py
src/decifra/credit/merton.py
src/decifra/credit/capacity.py
src/decifra/funds/cvm.py           # INF_DIARIO, CDA
src/decifra/funds/edgar.py
src/decifra/schemas/               # Profile, Credit&Debt Matrix, Val Waterfall
frontend/                          # React dark-mode UI
docs/schemas/                      # JSON Schema contracts
```

Do **not** replace or “patch away” working FCFF/WACC DCF or peer credit scoring; add complementary engines and unified output schemas on top.

---

## 5. Improvement IDs

Tracked in [`docs/improvements/LOG.md`](../improvements/LOG.md) as `IMP-020`… and automation stubs in [`AUTOMATION.md`](../improvements/AUTOMATION.md) as `AUTO-008`….
