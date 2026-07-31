---
name: decifra-aar
description: >-
  Write decifra-invest-agent After Action Reports and refresh the human HTML session
  dashboard. Use at session end, handoff, or when the user asks for AAR /
  session documentation / dashboard update.
---

# decifra-invest-agent AAR

## When

End of session, handoff, or after automation that needs a documented trace.

## Steps

1. Follow `docs/workflows/session-closeout.md` and `docs/agents/aar-writer.md`.
2. Copy `docs/aar/_TEMPLATE.md` → `docs/aar/YYYY-MM-DD-<slug>.md` (or `automation/` for sync runs).
3. Fill mandatory sections **verbatim structure**:
   1. Plan / purpose / objective
   2. What actually happened
   3. Gaps
   4. Lessons
   5. Improvements (also append `docs/improvements/LOG.md` for product gaps and/or `docs/improvements/AUTOMATION.md` for automation meta)
4. Update `docs/aar/INDEX.md`.
5. Optionally add prompts to `docs/prompts/FUTURE_AGENTS.md`.
6. Refresh dashboard (**required**; `scripts/sync_pilot.py` does this automatically on automation runs):

```bash
.\.venv\Scripts\python.exe scripts/update_session_dashboard.py
```

Human view: `docs/dashboard/index.html`. Agent sources stay `.md` under `docs/`.
