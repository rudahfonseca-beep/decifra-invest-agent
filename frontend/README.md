# decifra research UI (Terminal Dark)

Institutional **Unified Capital Analyst** shell: Vite + React 18 + Tailwind + lucide-react.

Layout: fixed sidebar (brand + live pipeline status) · header search (CNPJ / ticker / ISIN) · cross-asset opportunity screener · action catalyst feed. Detail views render Phase 5 schema samples.

```bash
cd frontend
npm install
npm run dev
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
