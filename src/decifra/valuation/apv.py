"""Adjusted Present Value (APV) complementary to FCFF/WACC DCF.

V_L = V_U + PV(Tax Shield) - PV(Distress Costs)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class APVResult:
    v_u: float
    pv_tax_shield: float
    pv_distress_costs: float
    v_l: float
    tax_rate: float
    methodology: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def pv_annuity(cashflow: float, rate: float, years: int) -> float:
    if years <= 0:
        return 0.0
    if abs(rate) < 1e-12:
        return cashflow * years
    return cashflow * (1.0 - (1.0 + rate) ** (-years)) / rate


def compute_apv(
    *,
    unlevered_fcff: list[float],
    unlevered_cost_of_capital: float,
    debt_interest: list[float] | None = None,
    tax_rate: float = 0.34,
    distress_cost_pv: float = 0.0,
    terminal_growth: float = 0.0,
) -> APVResult:
    """Discount unlevered FCFF at ku; add PV of interest tax shields; subtract distress.

    ``debt_interest[t]`` is period interest; tax shield = interest * tax_rate.
    Terminal value on last FCFF uses Gordon growth when terminal_growth > 0.
    """
    ku = unlevered_cost_of_capital
    interests = debt_interest or [0.0] * len(unlevered_fcff)
    if len(interests) < len(unlevered_fcff):
        interests = list(interests) + [0.0] * (len(unlevered_fcff) - len(interests))

    v_u = 0.0
    pv_ts = 0.0
    n = len(unlevered_fcff)
    for t, fcff in enumerate(unlevered_fcff, start=1):
        disc = (1.0 + ku) ** t
        cash = fcff
        if t == n and terminal_growth and ku > terminal_growth:
            tv = fcff * (1.0 + terminal_growth) / (ku - terminal_growth)
            cash += tv
        v_u += cash / disc
        shield = float(interests[t - 1]) * tax_rate
        pv_ts += shield / disc

    v_l = v_u + pv_ts - distress_cost_pv
    return APVResult(
        v_u=v_u,
        pv_tax_shield=pv_ts,
        pv_distress_costs=distress_cost_pv,
        v_l=v_l,
        tax_rate=tax_rate,
        methodology=[
            "V_L = V_U + PV(Tax Shield) - PV(Distress Costs)",
            f"Discount rate ku={ku}",
            f"Tax shield = interest * tax_rate ({tax_rate})",
            "Complementary to FCFF/WACC DCF; does not replace dcf.py",
        ],
    )
