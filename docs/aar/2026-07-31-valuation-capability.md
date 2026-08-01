---
id: 2026-07-31-valuation-capability
date: 2026-07-31
title: Valuation capability (DCF + trading multiples)
session_type: agent
transcript_id: "f3aae1ed-397d-497f-b283-9e551928931b"
status: completed
---

# AAR: Valuation capability (DCF + trading multiples)

## 1. Plan / purpose / objective

Add a full equity **valuation** capability to decifra-invest-agent: a DCF (FCFF/WACC)
model and trading multiples (P/E, EV/EBITDA, EV/Revenue, EV/EBIT, P/B), both with
data-grounded, fully user-overridable default assumptions, free-choice company
comparison, and a transparent "how these numbers were built" methodology section —
exposed via `decifra valuation ...` CLI commands and a new Streamlit "Valuation" tab.
Planned and executed as 5 stacked PRs (data layer → DCF engine + multiples in
parallel → spec/assemble/CLI → dashboard + docs), following the existing
`report/`/`credit/` module pattern.

## 2. What actually happened

Implemented the full plan end to end on 5 branches, each pushed and opened as its own
PR against the previous stage's branch:

- [PR #2](https://github.com/rudahfonseca-beep/decifra-invest-agent/pull/2) `feat/valuation-data-layer` — `config.py` constants, `valuation/historical.py`
  (multi-year annual DFP series), `valuation/market_data.py` (cached price/shares/market
  cap + Ibovespa index + local OLS beta regression).
- [PR #3](https://github.com/rudahfonseca-beep/decifra-invest-agent/pull/3) `feat/valuation-dcf-engine` — `valuation/assumptions.py` (`DcfAssumptions` +
  `build_default_assumptions()` with a traceable `AssumptionNote` per field),
  `valuation/dcf.py` (FCFF projection, WACC, terminal value, sensitivity grid).
- [PR #4](https://github.com/rudahfonseca-beep/decifra-invest-agent/pull/4) `feat/valuation-multiples` — `valuation/multiples.py` (`compute_multiples()` +
  `relative_valuation()` against user-chosen comparables).
- [PR #5](https://github.com/rudahfonseca-beep/decifra-invest-agent/pull/5) `feat/valuation-cli` — `valuation/spec.py`, `assemble.py`, `generate.py`
  (persisted `spec.json`/`context.json`/`valuation.md` under `data/valuations/{slug}/`),
  `decifra valuation dcf|multiples|build` CLI commands.
- `feat/valuation-dashboard-docs` (this session's final branch, not yet opened as a
  PR pending user confirmation of the 5-PR split) — Streamlit "Valuation" tab
  (editable assumptions, comparable multiselect, sensitivity heatmap, methodology
  expander, artifact download), README section, `docs/workflows/valuation.md`,
  `.cursor/skills/decifra-valuation/SKILL.md`, this AAR.

All 71 tests pass (`pytest -q`); manual CLI smoke tests against real local PETR4 data
(`decifra valuation dcf|multiples|build --ticker PETR4 --peers VALE3,CSNA3`) and a
headless Streamlit boot check both succeeded.

**Critical bug caught during integration testing, not unit testing**: CVM statements
report monetary accounts in thousands of reais (`ESCALA_MOEDA=MIL`). The first
end-to-end DCF run against real PETR4 data returned a per-share value ~1000x too low
(R$0.22 vs. a real price of R$43). Root cause: `valuation/historical.py` was returning
raw CVM figures (thousands scale) while market data (price × shares) is absolute
scale, and `dcf.py` additionally preferred a `credit/metrics.py` fallback that is
*never* rescaled (by design — it only computes scale-invariant ratios there). Fixed by
normalizing every monetary figure in `historical.py` to absolute reais via
`ESCALA_MOEDA`, and by making `dcf.py` prefer the (now-correct) historical series over
the `credit` module's native-scale fallback, rescaling that fallback by 1000 when it
is used. Backported this fix as its own commit onto PR #2 and PR #3 (not just the
final branch) so each PR is independently correct if merged and reviewed standalone.
Added a regression test (`test_mil_scale_normalized_to_absolute_reais`) and a numeric
coercion fix (`pd.to_numeric` on every historical column) for a related latent bug
where an all-missing account column raised `TypeError` on unary negation.

## 3. Gaps

- Shares-outstanding has no EPS-implied fallback (planned as "nice to have" in the
  original plan) — if `yfinance` has no data for a ticker, per-share values are
  simply unavailable (with a warning) rather than derived from `net_income / EPS`.
  EV-based figures still work.
- Default DCF assumptions are directionally reasonable but not tuned to reproduce
  market price — e.g. the PETR4 smoke run showed ~560% "upside" at pure defaults.
  This is by design (defaults are transparent and overridable, not a price target),
  but it means the very first thing a user sees looks like a huge mispricing signal;
  worth a UI callout that default DCF outputs are a starting point, not a
  recommendation.
- No dedicated CLI unit tests (`tests/test_cli.py` doesn't exist for any command
  group in this repo yet, not just valuation) — verified via manual smoke runs only,
  consistent with the existing `report` CLI's test coverage pattern.
- The 5th PR (`feat/valuation-dashboard-docs`) was not opened as a GitHub PR in this
  session; branch is pushed-ready but the PR itself should be opened in the next
  session or on user confirmation.
- Sensitivity grid recomputes the full DCF 25 times per render; each call re-reads
  local CSVs (`build_annual_history`, `extract_kpis`) unless the internal `_hist`/
  `_kpis`/`_market` hooks are used (only `sensitivity_grid()` itself does this
  internally — fine for CLI use, worth profiling if the Streamlit tab feels slow on
  a cold cache).

## 4. Lessons

- **Always sanity-check a new absolute-monetary-value feature against a real,
  known price/market-cap number before calling it done** — internally consistent
  unit tests (with hand-picked, self-consistent fixture numbers) will not catch a
  systematic scale bug like CVM's thousands-of-reais convention, because the test
  fixtures never mix two differently-scaled real data sources. Only an end-to-end
  run against real local data (PETR4) surfaced the 1000x error.
- When one module (`historical.py`) starts rescaling values that a sibling module
  (`credit/metrics.py`) intentionally leaves in a different scale for good reason
  (ratios are scale-invariant), every place that *reads from both* is a latent bug
  waiting to happen. Grep for cross-module monetary-value fallbacks whenever a new
  scale convention is introduced, not just at the point of introduction.
- Stacked PRs with local-only branches (no real remote CI/reviewer yet) let you
  keep iterating past PR1/PR2 while still fixing a bug discovered downstream —
  but remember to **backport the fix commit to the earlier branches too**, or the
  earlier PRs will look broken/incomplete if reviewed or merged in isolation.
- `git checkout <branch> -- <paths>` is a clean way to backport a specific file's
  fixed content across sibling branches without rebasing/force-pushing, when the
  branches don't otherwise depend on each other's history for those files.
- PowerShell doesn't support bash heredoc (`<<'EOF'`) for `gh pr create --body`;
  write the body to a temp markdown file and use `--body-file` instead.

## 5. Improvements

| ID | Improvement | Priority | Status |
|----|-------------|----------|--------|
| IMP-015 | Add EPS-implied shares-outstanding fallback when yfinance has no data for a ticker | low | open |
| IMP-016 | Add a "defaults are a starting point, not a price target" callout in the Streamlit Valuation tab and `valuation.md` when `upside_pct` is extreme (e.g. \|upside\| > 100%) | med | open |
| IMP-017 | Open PR for `feat/valuation-dashboard-docs` (Streamlit tab + docs) once the 5-PR split is confirmed with the user | high | open |
| IMP-018 | Profile/cache `sensitivity_grid()` + Streamlit Valuation tab cold-start cost; consider `st.cache_data` around `build_default_assumptions`/`discount_cash_flow` keyed by (ticker, peers, years) | low | open |
