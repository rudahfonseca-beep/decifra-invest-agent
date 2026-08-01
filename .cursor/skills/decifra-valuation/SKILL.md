---
name: decifra-valuation
description: >-
  Run decifra-invest-agent equity valuation: DCF (FCFF/WACC) and trading
  multiples with data-grounded, fully overridable defaults. Use for valuation
  smoke tests, assumption/methodology debugging, or Streamlit Valuation tab
  help.
---

# decifra-invest-agent valuation

## Commands

```bash
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --peers VALE3,CSNA3
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --terminal-growth 0.03 --beta 1.1 --wacc 0.12
.\.venv\Scripts\python.exe -m decifra valuation multiples --ticker PETR4 --peers VALE3,CSNA3 --stat median
.\.venv\Scripts\python.exe -m decifra valuation build --ticker PETR4 --peers VALE3,CSNA3
.\.venv\Scripts\python.exe -m decifra valuation build --spec docs/examples/valuation-spec.petr4.json
.\.venv\Scripts\python.exe -m decifra dashboard   # "Valuation" tab
```

## Behavior

- **DCF**: FCFF projection (revenue growth fades from year-1 default toward terminal growth,
  flat EBIT margin, D&A/capex/ΔNWC as % of revenue) discounted at WACC (CAPM cost of
  equity + market-value weights). Gordon-growth terminal value; terminal growth is
  auto-clipped below WACC with a warning if the user pushes it too high.
- **Multiples**: P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B computed from the same local
  data, applied against any user-chosen comparables (not limited to the same
  `industry_group` — that's only the UI's *default* peer suggestion).
- **Defaults are all traceable**: `build_default_assumptions()` returns an
  `AssumptionNote` per field with the exact formula/historical figures used —
  this powers the "How these numbers were built" section in the CLI table,
  Streamlit expander, and `valuation.md`.
- Every default is a plain field on `DcfAssumptions` — override any subset via
  CLI flags, a JSON file (`--assumptions`), a full spec (`--spec`), or the
  Streamlit inputs.
- Always writes `data/valuations/{slug}/` → `spec.json`, `context.json`, `valuation.md`
  (offline markdown, no LLM call).
- Code: `src/decifra/valuation/` (`historical`, `market_data`, `assumptions`, `dcf`,
  `multiples`, `spec`, `assemble`, `generate`).

## Critical invariant: currency scale

CVM statements report monetary accounts in **thousands of reais**
(`ESCALA_MOEDA=MIL`). `valuation/historical.py` normalizes every monetary
figure it extracts to **absolute reais** so it can be safely combined with
market data (price × shares, already absolute). `credit/metrics.py`
deliberately does **not** do this rescaling — it only ever computes
scale-invariant ratios. Never mix a `credit.metrics.extract_kpis()` monetary
figure directly with a `valuation` monetary figure without multiplying the
`credit` figure by 1000 first (see `dcf.py`'s `_CVM_THOUSANDS_SCALE`
fallback). Getting this wrong silently produces plausible-looking but
1000x-wrong per-share values — always sanity-check a fresh valuation run
against the ticker's real current price.

## Workflow

`docs/workflows/valuation.md` · spec example `docs/examples/valuation-spec.petr4.json`
