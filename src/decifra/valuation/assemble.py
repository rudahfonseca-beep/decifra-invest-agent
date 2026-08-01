"""Assemble a factual ValuationContext (DCF + multiples + methodology) from a spec."""

from __future__ import annotations

from typing import Any

from decifra.valuation.assumptions import DcfAssumptions, build_default_assumptions
from decifra.valuation.dcf import discount_cash_flow, sensitivity_grid
from decifra.valuation.multiples import relative_valuation
from decifra.valuation.spec import ValuationSpec

DISCLAIMER = (
    "Research-grade valuation from local CVM financials and live market quotes. "
    "Every default assumption is disclosed with its formula and rationale below — "
    "override any of them. Not investment advice."
)


def _merge_assumptions(spec: ValuationSpec) -> tuple[DcfAssumptions, list[dict[str, Any]]]:
    defaults, notes = build_default_assumptions(
        spec.ticker, peers=spec.comparatives, forecast_years=spec.forecast_years
    )
    merged = defaults.to_dict()
    overrides = {k: v for k, v in spec.dcf_assumptions.items() if v is not None}
    merged.update(overrides)
    assumptions = DcfAssumptions.from_dict(merged)
    note_dicts = [n.to_dict() for n in notes]
    for key in overrides:
        note_dicts.append(
            {
                "key": key,
                "label": key,
                "value": overrides[key],
                "formula": "user override",
                "rationale": "Value provided directly by the user, replacing the computed default.",
            }
        )
    return assumptions, note_dicts


def assemble_context(spec: ValuationSpec) -> dict[str, Any]:
    """Build a JSON-serializable ValuationContext from a validated ValuationSpec."""
    assumptions, methodology = _merge_assumptions(spec)
    dcf_result = discount_cash_flow(spec.ticker, assumptions, peers=spec.comparatives)
    grid = sensitivity_grid(spec.ticker, assumptions)

    multiples_block: dict[str, Any] | None = None
    if spec.comparatives:
        multiples_block = relative_valuation(
            spec.ticker, spec.comparatives, stat=spec.multiples_stat
        ).to_dict()

    return {
        "title": spec.default_title(),
        "ticker": spec.ticker,
        "comparatives": list(spec.comparatives),
        "multiples_stat": spec.multiples_stat,
        "dcf": dcf_result.to_dict(),
        "sensitivity": grid,
        "multiples": multiples_block,
        "methodology": methodology,
        "disclaimer": DISCLAIMER,
    }
