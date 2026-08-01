"""Debt capacity covenant flags (research gates)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

NET_DEBT_EBITDA_MAX = 3.5
DSCR_MIN = 1.25


@dataclass
class CapacityFlag:
    metric: str
    value: float | None
    threshold: float
    operator: str
    breach: bool
    lineage: dict[str, Any]


@dataclass
class CapacityResult:
    net_debt_ebitda: CapacityFlag
    dscr: CapacityFlag
    any_breach: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "net_debt_ebitda": asdict(self.net_debt_ebitda),
            "dscr": asdict(self.dscr),
            "any_breach": self.any_breach,
        }


def evaluate_capacity(
    *,
    net_debt: float | None,
    ebitda: float | None,
    ocf_or_ebitda_proxy: float | None,
    debt_service: float | None,
    lineage: dict[str, Any] | None = None,
) -> CapacityResult:
    """Flag breaches: Net Debt/EBITDA <= 3.5x; DSCR >= 1.25x.

    DSCR here uses ``ocf_or_ebitda_proxy / debt_service`` (research proxy).
    """
    lin = lineage or {"source_doc": "capacity"}
    nd_ebitda = None
    if net_debt is not None and ebitda not in (None, 0):
        nd_ebitda = float(net_debt) / float(ebitda)
    nd_flag = CapacityFlag(
        metric="net_debt_ebitda",
        value=nd_ebitda,
        threshold=NET_DEBT_EBITDA_MAX,
        operator="<=",
        breach=bool(nd_ebitda is not None and nd_ebitda > NET_DEBT_EBITDA_MAX),
        lineage=lin,
    )

    dscr = None
    if (
        ocf_or_ebitda_proxy is not None
        and debt_service not in (None, 0)
    ):
        dscr = float(ocf_or_ebitda_proxy) / float(debt_service)
    dscr_flag = CapacityFlag(
        metric="dscr",
        value=dscr,
        threshold=DSCR_MIN,
        operator=">=",
        breach=bool(dscr is not None and dscr < DSCR_MIN),
        lineage=lin,
    )
    return CapacityResult(
        net_debt_ebitda=nd_flag,
        dscr=dscr_flag,
        any_breach=nd_flag.breach or dscr_flag.breach,
    )
