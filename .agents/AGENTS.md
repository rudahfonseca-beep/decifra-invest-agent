# Decifra Invest Agent Guidelines

## Data Sources & Product Boundaries
- **Local Lake**: under `data/companies/{TICKER}/` (gitignored) + `data/cache/cvm/` + `data/universe/`.
- **Sources**: B3 (Ibovespa + CNPJ), CVM Dados Abertos (DFP/ITR/IPE), brapi/yfinance (prices), company RI sites (best-effort).
- **Credit Scores**: Research-grade industry peer ranks, not bureau/Serasa ratings and not Open Finance / Pluggy personal banking.
- **Store**: Filesystem store — not SQL. Prefer README + `docs/aar/` over re-deriving the layout.

## Documentation & Exploration Strategy
- Before launching a broad explore:
  1. Read `README.md`
  2. Read `docs/aar/INDEX.md` and the latest relevant AAR
  3. Skim `docs/improvements/LOG.md` and `docs/improvements/AUTOMATION.md` for known gaps
- Only do a full greenfield explore when those sources are missing or clearly outdated for the task.

## Mandatory Session AAR Documentation
At the end of every `decifra-invest-agent` session (and after automation runs):
1. Write `docs/aar/YYYY-MM-DD-<slug>.md` from `docs/aar/_TEMPLATE.md` with sections:
   - Plan / purpose / objective
   - What actually happened
   - Gaps
   - Lessons
   - Improvements (also append `docs/improvements/LOG.md` and/or `docs/improvements/AUTOMATION.md`)
2. Update `docs/aar/INDEX.md` and append follow-ups to the improvements logs.
3. Add useful prompts to `docs/prompts/FUTURE_AGENTS.md` when lessons suggest them.
4. Run `.\.venv\Scripts\python.exe scripts/update_session_dashboard.py` (required sync_pilot closeout too).
5. Automation traces go under `docs/aar/automation/`. Automation meta: `docs/improvements/AUTOMATION.md`. See `docs/workflows/session-closeout.md` and skill `decifra-aar`.

## Windows Virtual Environment & Executables
- Prefer `.\.venv\Scripts\python.exe -m decifra …` or activate `.\.venv\Scripts\Activate.ps1`.
- Prefer `.\.venv\Scripts\python.exe scripts\….py` for project scripts.
- Do **not** assume a global `decifra` command is on PATH after `pip install`.
- If `.venv` is missing: `python -m venv .venv` then `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"`.
