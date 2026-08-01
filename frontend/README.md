# decifra research UI (Terminal Dark)

Institutional **Unified Capital Analyst** shell: Vite + React 18 + Tailwind + lucide-react.

Layout: fixed sidebar (brand + live pipeline status) · header search (CNPJ / ticker / ISIN) · Streamlit-parity research views (industries, tickers, credit overview/detail, valuation, report builder, coverage) · opportunity screener · catalyst feed · Phase 5 schema detail panes.

```bash
cd frontend
npm install
npm run dev
```

### Live lake feed (IMP-037)

In another terminal:

```bash
.\.venv\Scripts\python.exe -m decifra schemas serve --port 8765
```

Vite proxies `/api/*` → `http://127.0.0.1:8765`. Without the API, the UI falls back to `public/sample/`.

Refresh committed sample fixtures from the lake:

```bash
.\.venv\Scripts\python.exe -m decifra schemas export-ui --out frontend/public/sample --limit 8
```

Samples under `public/sample/`:

| File | Role |
|------|------|
| `opportunity_screener.json` | Equity APV + credit leverage / Merton table |
| `catalyst_feed.json` | Right-rail impact timeline |
| `company_profile.json` | Profile detail |
| `credit_debt_matrix.json` | Credit & debt detail |
| `valuation_waterfall.json` | Waterfall detail |

Streamlit remains the interim research UI until live lake/API cutover (IMP-037).
