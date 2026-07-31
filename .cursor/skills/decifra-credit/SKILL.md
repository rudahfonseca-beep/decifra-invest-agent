---
name: decifra-credit
description: >-
  Run decifra-invest-agent creditworthiness scoring and Streamlit dashboard. Use for
  industry peer scores, credit smoke tests, or metric/signal debugging.
---

# decifra-invest-agent credit

## Commands

```bash
.\.venv\Scripts\python.exe -m decifra credit
.\.venv\Scripts\python.exe -m decifra credit --industry Energy
.\.venv\Scripts\python.exe -m decifra dashboard
```

Extras: `pip install -e ".[dashboard]"` once for Streamlit.

## Behavior

- Research-grade peer ranks within `industry_group` (not bureau credit).
- Separate scorecards for bank/insurer vs non-financial.
- Optional keyword penalty from notices/transcripts (capped).
- Known issue: empty **interest_coverage** for PETR4 (IMP-004).

## Workflow

`docs/workflows/credit-smoke.md` · playbook `docs/agents/credit-qa.md`
