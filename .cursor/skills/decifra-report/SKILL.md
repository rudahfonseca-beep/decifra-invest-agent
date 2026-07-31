---
name: decifra-report
description: >-
  Build decifra-invest-agent credit/equity research reports: assemble local KPI context,
  pack an LLM prompt, optionally generate interactive HTML. Use for report
  smoke tests, spec validation, or Streamlit Report builder help.
---

# decifra-invest-agent report builder

## Commands

```bash
.\.venv\Scripts\python.exe -m decifra report build --mode credit --company PETR4 --industry Energy
.\.venv\Scripts\python.exe -m decifra report build --mode equity --company VALE3 --kpi roe,net_margin,ebit_margin
.\.venv\Scripts\python.exe -m decifra report build --spec docs/examples/report-spec.credit.json
.\.venv\Scripts\python.exe -m decifra report build --spec docs/examples/report-spec.credit.json --generate
.\.venv\Scripts\python.exe -m decifra dashboard
```

## Behavior

- Shared builder: `credit` | `equity` mode (same picker; different default KPIs + prompt sections).
- Always writes `data/reports/{slug}/` → `spec.json`, `context.json`, `report.prompt.md`.
- `--generate` calls OpenAI-compatible chat (`OPENAI_API_KEY`) for `report.html`.
- Reuses `credit.scoring` / `credit.metrics` / signals — no parallel data path.
- Code: `src/decifra/report/` (`spec`, `assemble`, `prompt`, `html_scaffold`, `generate`).

## Workflow

`docs/workflows/report-build.md` · playbook `docs/agents/report-qa.md`
