# decifra research UI (Terminal Dark)

Institutional **Unified Capital Analyst** shell: Vite + React 18 + Tailwind + lucide-react.

Layout: fixed sidebar (brand + live pipeline status) · header search (CNPJ / ticker / ISIN) · Streamlit-parity research views (industries, tickers, credit overview/detail, valuation, report builder, coverage) · opportunity screener · catalyst feed · Phase 5 schema detail panes.

```bash
# From repo root — installs frontend/node_modules if missing, starts lake API + Vite
.\.venv\Scripts\python.exe -m decifra ui
# or: .\scripts\dev_ui.ps1
```

Vite proxies `/api/*` → `http://127.0.0.1:8765`. Use `--no-api` to skip the lake API (falls back to `public/sample/`).

Manual two-terminal flow (optional):

```bash
.\.venv\Scripts\python.exe -m decifra schemas serve --port 8765
cd frontend && npm install && npm run dev
```

Refresh committed sample fixtures + disk UI cache from the lake (also run by `sync_pilot` closeout):

```bash
.\.venv\Scripts\python.exe -m decifra schemas export-ui --out frontend/public/sample --limit 8
.\.venv\Scripts\python.exe -m decifra schemas warm-ui-cache --scope core
```

List/screener/credit APIs default to `scope=core` (IBOV ∪ watchlist) so full listed-equity universes stay responsive. Client state uses TanStack Query (shell vs ticker-scoped keys).

Samples under `public/sample/`:

| File | Role |
|------|------|
| `opportunity_screener.json` | Equity APV + credit leverage / Merton table |
| `catalyst_feed.json` | Right-rail impact timeline |
| `company_profile.json` | Profile detail |
| `credit_debt_matrix.json` | Credit & debt detail |
| `valuation_waterfall.json` | Waterfall detail |

Streamlit remains the interim research UI until live lake/API cutover (IMP-037).
