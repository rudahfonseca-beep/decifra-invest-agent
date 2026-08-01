"""ValuationSpec model and validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from decifra.config import DEFAULT_FORECAST_YEARS
from decifra.store.folders import list_tickers

VALID_STATS = {"median", "mean"}

_ASSUMPTION_KEYS = {
    "forecast_years",
    "revenue_growth_y1",
    "terminal_growth",
    "ebit_margin",
    "tax_rate",
    "da_pct_revenue",
    "capex_pct_revenue",
    "nwc_pct_revenue",
    "risk_free_rate",
    "equity_risk_premium",
    "country_risk_premium",
    "beta",
    "cost_of_debt",
    "wacc_override",
}


@dataclass
class ValuationSpec:
    ticker: str = ""
    comparatives: list[str] = field(default_factory=list)
    dcf_assumptions: dict[str, Any] = field(default_factory=dict)
    multiples_stat: str = "median"
    forecast_years: int = DEFAULT_FORECAST_YEARS
    title: str = ""

    def default_title(self) -> str:
        if self.title.strip():
            return self.title.strip()
        focus = self.ticker.upper() or "valuation"
        if self.comparatives:
            focus += f" vs {', '.join(self.comparatives)}"
        return f"Valuation — {focus}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ValuationSpec":
        return cls(
            ticker=str(data.get("ticker") or "").upper().strip(),
            comparatives=[str(c).upper().strip() for c in (data.get("comparatives") or []) if str(c).strip()],
            dcf_assumptions=dict(data.get("dcf_assumptions") or {}),
            multiples_stat=str(data.get("multiples_stat") or "median").lower().strip(),
            forecast_years=int(data.get("forecast_years") or DEFAULT_FORECAST_YEARS),
            title=str(data.get("title") or ""),
        )


class SpecValidationError(ValueError):
    """Raised when a valuation spec fails validation."""


def load_spec(path: str | Path) -> ValuationSpec:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecValidationError("Spec file must contain a JSON object")
    try:
        spec = ValuationSpec.from_dict(raw)
    except (ValueError, TypeError) as exc:
        raise SpecValidationError(str(exc)) from exc
    return validate_spec(spec)


def validate_spec(
    spec: ValuationSpec, *, known_tickers: list[str] | None = None
) -> ValuationSpec:
    """Validate and normalize a ValuationSpec. Returns the same instance after checks."""
    if not spec.ticker:
        raise SpecValidationError("A subject ticker is required")

    tickers = {t.upper() for t in (known_tickers if known_tickers is not None else list_tickers())}
    if tickers and spec.ticker.upper() not in tickers:
        raise SpecValidationError(f"Unknown ticker: {spec.ticker}")

    comparatives: list[str] = []
    for c in spec.comparatives:
        t = c.upper().strip()
        if not t or t == spec.ticker.upper():
            continue
        if tickers and t not in tickers:
            raise SpecValidationError(f"Unknown comparative ticker: {t}")
        if t not in comparatives:
            comparatives.append(t)
    spec.comparatives = comparatives

    if spec.multiples_stat not in VALID_STATS:
        raise SpecValidationError(
            f"Invalid multiples_stat '{spec.multiples_stat}'; expected one of {sorted(VALID_STATS)}"
        )

    if not (2 <= spec.forecast_years <= 10):
        raise SpecValidationError("forecast_years must be between 2 and 10")

    unknown_keys = set(spec.dcf_assumptions) - _ASSUMPTION_KEYS
    if unknown_keys:
        raise SpecValidationError(f"Unknown dcf_assumptions key(s): {', '.join(sorted(unknown_keys))}")

    return spec
