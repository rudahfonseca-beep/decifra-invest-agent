# Subagent playbook: AAR writer

## Goal

End-of-session After Action Report + human HTML dashboard refresh.

## Procedure

1. Gather: user objective, what was implemented, commands run, open gaps, lessons.
2. Create `docs/aar/YYYY-MM-DD-<slug>.md` from `_TEMPLATE.md`.
3. Mandatory sections:
   1. Plan / purpose / objective
   2. What actually happened
   3. Gaps
   4. Lessons
   5. Improvements (table + append `docs/improvements/LOG.md` and/or `docs/improvements/AUTOMATION.md`)
4. Update `docs/aar/INDEX.md`.
5. Add any new prompts to `docs/prompts/FUTURE_AGENTS.md`.
6. Run (required; also automatic via `sync_pilot`):

```bash
.\.venv\Scripts\python.exe scripts/update_session_dashboard.py
```

7. Confirm `docs/dashboard/index.html` lists the new session (and Automation opportunities section when relevant).

## Skill

`.cursor/skills/decifra-aar/SKILL.md`
