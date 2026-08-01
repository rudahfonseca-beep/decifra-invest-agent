# Workflow: Valuation smoke

Verify the DCF + trading-multiples valuation capability after code or data changes.

## Prerequisites

```bash
.\.venv\Scripts\activate
pip install -e ".[dev,dashboard]"
# Financials must exist for subject + comparative tickers
.\.venv\Scripts\python.exe -m decifra status --ticker PETR4
```

## Steps (CLI — no API key, no LLM)

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_valuation_*.py -q
```

```bash
# DCF (FCFF/WACC) — data-grounded defaults, printed with the methodology used
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --peers VALE3,CSNA3

# Override any assumption directly on the CLI
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --terminal-growth 0.03 --beta 1.1 --wacc 0.12

# Trading multiples vs. user-chosen comparables
.\.venv\Scripts\python.exe -m decifra valuation multiples --ticker PETR4 --peers VALE3,CSNA3 --stat median

# Full artifact set (spec.json, context.json, valuation.md) under data/valuations/
.\.venv\Scripts\python.exe -m decifra valuation build --ticker PETR4 --peers VALE3,CSNA3
.\.venv\Scripts\python.exe -m decifra valuation build --spec docs/examples/valuation-spec.petr4.json
```

Open the printed folder under `data/valuations/`:

| File | Check |
|------|--------|
| `spec.json` | Ticker, comparatives, overrides match the CLI flags / spec file |
| `context.json` | `dcf`, `multiples` (when comparatives given), `sensitivity`, `methodology` are all populated |
| `valuation.md` | FCFF table, multiples table, and "How these numbers were built" section render with real numbers |

## Streamlit

```bash
.\.venv\Scripts\python.exe -m decifra dashboard
```

1. Open the **Valuation** tab
2. Pick a subject ticker — comparatives default to the same `industry_group` but accept any ticker
3. Every DCF assumption is pre-filled and editable; **Reset assumptions to defaults** restores the computed defaults
4. Check the WACC × terminal-growth sensitivity heatmap renders
5. Expand **How these numbers were built** — every default should cite a real formula/number for this company
6. **Save valuation artifacts** → download `valuation.md` / `context.json`

## Checks

- Unknown ticker / comparative / `multiples_stat` / out-of-range `forecast_years` → validation error (CLI exit 1 / Streamlit error)
- When `|upside_pct| > 100%`, Streamlit and `valuation.md` show: **Defaults are a starting point, not a price target** (IMP-016)
- Missing shares outstanding (e.g. thin/no yfinance coverage) → try B3 artifact then EPS/market-cap implied shares (IMP-015); else DCF still returns enterprise value with a warning instead of crashing
- Terminal growth ≥ WACC is auto-clipped with a warning, never silently produces a negative/undefined terminal value
- CVM statements report accounts in **thousands of reais** — `valuation/historical.py` normalizes to absolute reais before combining with market data (price × shares); this is the single most important place to re-check after touching account extraction, since a scale mismatch silently produces plausible-looking but wrong (1000x) per-share values
- Peer count < 2 for multiples flags `peer_benchmark: false` (directional, not a robust benchmark) — matches the existing `credit/scoring.py` convention

## Skill / methodology

- Skill: `.cursor/skills/decifra-valuation/SKILL.md`
- Methodology detail: see the module docstrings in `src/decifra/valuation/assumptions.py` and `src/decifra/valuation/dcf.py`
- Spec example: `docs/examples/valuation-spec.petr4.json`
