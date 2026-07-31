# Workflow: Session closeout

Run at the end of every agent session.

## Steps

1. Copy `docs/aar/_TEMPLATE.md` → `docs/aar/YYYY-MM-DD-<slug>.md`.
2. Fill sections **1–5** (plan, happened, gaps, lessons, improvements).
3. Set frontmatter (`id`, `date`, `title`, `session_type: agent`, `transcript_id`, `status`).
4. Append new improvement rows to `docs/improvements/LOG.md` (product/data) and/or `docs/improvements/AUTOMATION.md` (automation meta).
5. Add a row to `docs/aar/INDEX.md`.
6. Optionally add prompts to `docs/prompts/FUTURE_AGENTS.md`.
7. Refresh the human dashboard (**required**; sync_pilot does this automatically):

```bash
.\.venv\Scripts\python.exe scripts/update_session_dashboard.py
```

8. Open `docs/dashboard/index.html` and confirm the session card appears.

## Skill / playbook

- Skill: `.cursor/skills/decifra-aar/SKILL.md`
- Playbook: `docs/agents/aar-writer.md`
