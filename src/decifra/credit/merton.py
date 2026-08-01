"""Merton structural model: equity as call on assets; Distance to Default."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

try:
    from scipy.stats import norm
except Exception:  # pragma: no cover - scipy may be heavy; fall back
    norm = None  # type: ignore


def _n(x: float) -> float:
    if norm is not None:
        return float(norm.cdf(x))
    # Abramowitz–Stegun approximation
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


@dataclass
class MertonResult:
    asset_value: float
    debt_face: float
    risk_free: float
    horizon_years: float
    asset_vol: float
    d1: float
    d2: float
    equity_value: float
    debt_value: float
    distance_to_default: float
    default_probability: float
    methodology: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def merton_dtd(
    *,
    asset_value: float,
    debt_face: float,
    risk_free: float,
    horizon_years: float,
    asset_vol: float,
) -> MertonResult:
    """European call equity; DtD = d2 under Merton assumptions."""
    v, d, r, t, sig = (
        float(asset_value),
        float(debt_face),
        float(risk_free),
        float(horizon_years),
        float(asset_vol),
    )
    if v <= 0 or d <= 0 or t <= 0 or sig <= 0:
        raise ValueError("asset_value, debt_face, horizon_years, asset_vol must be > 0")

    sqrt_t = math.sqrt(t)
    d1 = (math.log(v / d) + (r + 0.5 * sig * sig) * t) / (sig * sqrt_t)
    d2 = d1 - sig * sqrt_t
    equity = v * _n(d1) - d * math.exp(-r * t) * _n(d2)
    debt_value = v - equity
    dtd = d2
    pd = _n(-d2)
    return MertonResult(
        asset_value=v,
        debt_face=d,
        risk_free=r,
        horizon_years=t,
        asset_vol=sig,
        d1=d1,
        d2=d2,
        equity_value=equity,
        debt_value=debt_value,
        distance_to_default=dtd,
        default_probability=pd,
        methodology=[
            "Equity = Call(V, D, r, T, sigma_V) Black-Scholes/Merton",
            "Distance to Default = d2",
            "PD = N(-d2)",
        ],
    )
