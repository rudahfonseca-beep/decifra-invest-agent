# Workflow: Report build smoke

Verify the shared credit/equity report builder after code or data changes.

## Prerequisites

```bash
.\.venv\Scripts\activate
pip install -e ".[dev,dashboard]"
# Financials must exist for subject tickers (see sync-pilot / credit-smoke)
.\.venv\Scripts\python.exe -m decifra status --ticker PETR4
```

## Steps (CLI — no API key)

```bash
.\.venv\Scripts\python.exe -m pytest tests/test_report_spec.py tests/test_report_assemble.py tests/test_report_prompt.py -q

.\.venv\Scripts\python.exe -m decifra report build ^
  --mode credit ^
  --company PETR4 ^
  --industry Energy ^
  --compare-company VALE3 ^
  --no-signals
```

Open the printed folder under `data/reports/`:

| File | Check |
|------|--------|
| `spec.json` | Mode, subjects, comparatives match the CLI flags |
| `context.json` | Company KPI values + industry ranked members are non-empty |
| `report.prompt.md` | Contains System + User sections, HTML scaffold, Plotly CDN |

## Optional HTML (needs `OPENAI_API_KEY` in `.env`)

```bash
.\.venv\Scripts\python.exe -m decifra report build --spec docs/examples/report-spec.credit.json --generate
```

Open `report.html` in a browser — charts/tables/narrative should be filled.

## Streamlit

```bash
.\.venv\Scripts\python.exe -m decifra dashboard
```

1. Open **Report builder** tab  
2. Mode = credit, subject company + industry, pick KPIs  
3. **Export prompt** → download `.md` / `.json`  
4. **Generate HTML** only if API key is set  

## Checks

- Empty subjects → validation error (CLI exit 1 / Streamlit error)
- Equity mode defaults include `roe`, `ebit_margin`, `net_margin`
- Artifacts land under `data/reports/{slug}/`
- Prompt alone is a valid deliverable without an API key

## Skill / playbook

- Skill: `.cursor/skills/decifra-report/SKILL.md`
- Playbook: `docs/agents/report-qa.md`
- Spec example: `docs/examples/report-spec.credit.json`
