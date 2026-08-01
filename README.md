# decifra-invest-agent

Ibovespa financial market research **data pipeline + CLI** (package/CLI: `decifra`).

Syncs official public data into one folder per ticker, then answers research questions from that local store.

## What it collects

For each Ibovespa constituent:

| Path | Content |
|------|---------|
| `data/companies/{TICKER}/meta.json` | Ticker, CNPJ, CVM code, RI URL |
| `financials/*.csv` | DRE, balance sheet, cash flow (CVM DFP/ITR) + prices |
| `notices/` | Fatos relevantes / comunicados (index + PDFs) |
| `transcripts/` | Call/presentation materials (index + PDFs + extracted text) |

## Install

```bash
cd decifra-invest-agent
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
copy .env.example .env          # optional keys
```

## Usage

```bash
# 1) Universe + folders
decifra sync universe

# 2) Financial statements (downloads CVM ZIPs — first run is slow)
decifra sync financials
decifra sync financials --ticker PETR4 --years 2022-2025

# 3) Market notices
decifra sync notices --ticker PETR4 --years 2024-2026

# 4) Call / presentation materials
decifra sync transcripts --ticker PETR4

# Full pipeline
decifra sync all --ticker PETR4

# Coverage
decifra status
decifra status --ticker VALE3

# Research questions (local data; optional LLM if OPENAI_API_KEY set)
decifra ask "Qual foi a receita líquida da VALE3 em 2024?"
decifra ask "Liste fatos relevantes da PETR4 em 2025"

# Creditworthiness (industry peer scores from local CVM data)
pip install -e ".[dashboard]"          # once — Streamlit + Plotly
decifra credit                         # Rich table
decifra credit --industry Energy
decifra dashboard                      # Streamlit UI (filter by industry)
```

Credit scores are **research-grade** (fundamental ratios + optional notice/transcript keyword penalties), ranked within industry groups. They are not bureau ratings.

## Report builder

Shared **credit / equity** report builder: pick companies, industries, and KPIs; the platform assembles local facts and packs an LLM prompt (optional HTML generation).

```bash
# Prompt + context under data/reports/ (no API key required)
.\.venv\Scripts\python.exe -m decifra report build --mode credit --company PETR4 --industry Energy --compare-company VALE3
.\.venv\Scripts\python.exe -m decifra report build --mode equity --company VALE3 --kpi roe,net_margin,ebit_margin

# From a JSON spec; optionally call the LLM for interactive HTML
.\.venv\Scripts\python.exe -m decifra report build --spec docs/examples/report-spec.credit.json
.\.venv\Scripts\python.exe -m decifra report build --spec docs/examples/report-spec.credit.json --generate

# Or use the Streamlit "Report builder" tab
.\.venv\Scripts\python.exe -m decifra dashboard
```

**How to check the product**

1. Unit tests: `.\.venv\Scripts\python.exe -m pytest tests/test_report_*.py -q`
2. CLI build (above) → open the printed path under `data/reports/`
3. Read `report.prompt.md` (paste into any LLM) and skim `context.json` for KPI facts
4. With `OPENAI_API_KEY`: `--generate` then open `report.html` in a browser
5. Dashboard → **Report builder** → Export prompt / Generate HTML

Full smoke checklist: [`docs/workflows/report-build.md`](docs/workflows/report-build.md) · skill [`.cursor/skills/decifra-report/SKILL.md`](.cursor/skills/decifra-report/SKILL.md)

Artifacts per run: `spec.json`, `context.json`, `report.prompt.md`, and `report.html` when `--generate` succeeds.

## Valuation (DCF + trading multiples)

Equity valuation with **data-grounded, fully overridable defaults**: FCFF/WACC DCF and
trading multiples (P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B), both against
comparables of your choice — not limited to the same industry.

```bash
# DCF — defaults come from this company's own multi-year CVM history + live market data
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --peers VALE3,CSNA3

# Override any assumption directly, or point --wacc at a number to bypass CAPM entirely
.\.venv\Scripts\python.exe -m decifra valuation dcf --ticker PETR4 --terminal-growth 0.03 --beta 1.1

# Trading multiples vs. comparables you pick
.\.venv\Scripts\python.exe -m decifra valuation multiples --ticker PETR4 --peers VALE3,CSNA3 --stat median

# Full artifact set (spec/context/markdown) under data/valuations/
.\.venv\Scripts\python.exe -m decifra valuation build --ticker PETR4 --peers VALE3,CSNA3
.\.venv\Scripts\python.exe -m decifra valuation build --spec docs/examples/valuation-spec.petr4.json

# Or use the Streamlit "Valuation" tab
.\.venv\Scripts\python.exe -m decifra dashboard
```

Every default (revenue growth, EBIT margin, tax rate, D&A/capex/ΔNWC intensity, beta,
cost of debt, WACC) is disclosed with its exact formula and this company's own numbers
in a "How these numbers were built" section — CLI table, Streamlit expander, and
`valuation.md` all show the same methodology.

Full smoke checklist: [`docs/workflows/valuation.md`](docs/workflows/valuation.md) · skill [`.cursor/skills/decifra-valuation/SKILL.md`](.cursor/skills/decifra-valuation/SKILL.md)

Artifacts per run: `spec.json`, `context.json`, `valuation.md` under `data/valuations/{slug}/`.

## Optional env vars

See [`.env.example`](.env.example):

- `BRAPI_API_KEY` — better quote history via [brapi.dev](https://brapi.dev) (falls back to Yahoo/`yfinance`)
- `OPENAI_API_KEY` — `decifra ask` summarization **and** `decifra report build --generate` HTML
- `OPENAI_BASE_URL` / `OPENAI_MODEL` — OpenAI-compatible endpoint (defaults to OpenAI + `gpt-4o-mini`)
## Sources

- **B3 Listados** — Ibovespa theoretical portfolio + company CNPJ enrichment
- **CVM Dados Abertos** — cadastro, DFP, ITR, IPE, fatos relevantes
- **Company RI sites** — best-effort harvest of call/presentation links

## Architecture target (Unified Financial Data Pipeline)

End-state vision (equity + credit + fixed income + funds) is documented under [`docs/architecture/`](docs/architecture/). **Not all layers are implemented yet** — current product remains Ibovespa + CVM DFP/ITR + research credit/valuation.

- Gap analysis (pillar Pass/Fail): [`docs/architecture/unified-pipeline-gap-analysis.md`](docs/architecture/unified-pipeline-gap-analysis.md)
- Phased roadmap: [`docs/architecture/unified-pipeline-roadmap.md`](docs/architecture/unified-pipeline-roadmap.md)
- Auditor skill: [`.cursor/skills/decifra-pipeline-auditor/SKILL.md`](.cursor/skills/decifra-pipeline-auditor/SKILL.md)

## Session docs & automation

- Agent AARs (markdown): [`docs/aar/`](docs/aar/) — see [`docs/aar/INDEX.md`](docs/aar/INDEX.md)
- Human dashboard (HTML): open [`docs/dashboard/index.html`](docs/dashboard/index.html)
- Sync pilot (coverage + AAR + **dashboard refresh**): `.\.venv\Scripts\python.exe scripts/sync_pilot.py`
- Refresh dashboard alone: `.\.venv\Scripts\python.exe scripts/update_session_dashboard.py`
- Improvements: [`docs/improvements/LOG.md`](docs/improvements/LOG.md) · automation meta: [`docs/improvements/AUTOMATION.md`](docs/improvements/AUTOMATION.md)
- Workflows: [`docs/workflows/`](docs/workflows/) · Cursor skills under [`.cursor/skills/`](.cursor/skills/)
- Report smoke: [`docs/workflows/report-build.md`](docs/workflows/report-build.md) · examples in [`docs/examples/`](docs/examples/)

## Notes

- First `sync financials` downloads multi‑MB yearly ZIPs into `data/cache/cvm/` and is idempotent.
- Transcripts in Brazil are often slides/audio, not clean text — extraction is best-effort.
- v1 universe is **Ibovespa only**.
- Prefer `.\.venv\Scripts\python.exe -m decifra` on Windows (global `decifra` may not be on PATH).
