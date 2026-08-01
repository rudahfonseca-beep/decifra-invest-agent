"""Cash flow waterfall: OCF -> mandatory debt service -> residual FCFE."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class WaterfallResult:
    ocf: float
    interest: float
    mandatory_amortization: float
    debt_service: float
    fcfe: float
    covered: bool
    lineage: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ocf_to_fcfe_waterfall(
    *,
    ocf: float,
    interest: float,
    mandatory_amortization: float = 0.0,
    capex_equity_financed: float = 0.0,
    net_borrowing: float = 0.0,
    lineage: dict[str, Any] | None = None,
) -> WaterfallResult:
    """Residual free cash flow to equity after mandatory debt service.

    FCFE ≈ OCF - interest - mandatory_amortization - equity_capex + net_borrowing
    (simplified research waterfall; not a full statement roll-forward).
    """
    debt_service = float(interest) + float(mandatory_amortization)
    fcfe = float(ocf) - debt_service - float(capex_equity_financed) + float(net_borrowing)
    return WaterfallResult(
        ocf=float(ocf),
        interest=float(interest),
        mandatory_amortization=float(mandatory_amortization),
        debt_service=debt_service,
        fcfe=fcfe,
        covered=float(ocf) >= debt_service,
        lineage=lineage
        or {
            "source_doc": "waterfall",
            "formula": "OCF - interest - mandatory_amortization - equity_capex + net_borrowing",
        },
    )
