# Workflow: Credit smoke

Quick health check of credit scoring after data or metric changes.

## Steps

```bash
.\.venv\Scripts\python.exe -m decifra credit --industry Energy
.\.venv\Scripts\python.exe -m decifra status --ticker PETR4
```

Optional UI:

```bash
.\.venv\Scripts\python.exe -m decifra dashboard
```

## Checks

- Energy ranking is non-empty
- Note any empty `interest_coverage` (known PETR4 gap — IMP-004)
- If scores regress unexpectedly, write an AAR and open an improvement

## Skill / playbook

- Skill: `.cursor/skills/decifra-credit/SKILL.md`
- Playbook: `docs/agents/credit-qa.md`
