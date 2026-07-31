"""KPI catalog and mode-specific defaults for the shared report builder."""

from __future__ import annotations

from typing import Literal

ReportMode = Literal["credit", "equity"]

# Display labels for picker / tables / prompts
KPI_LABELS: dict[str, str] = {
    "credit_score": "Credit score",
    "fundamental_score": "Fundamental score",
    "qualitative_penalty": "Qualitative penalty",
    "debt_to_equity": "Debt / Equity",
    "net_debt_to_cash": "Net Debt / Liquid Assets",
    "current_ratio": "Current Ratio",
    "interest_coverage": "Interest Coverage",
    "ocf_to_net_debt": "Op. CF / Net Debt",
    "net_margin": "Net Margin",
    "equity_to_assets": "Equity / Assets",
    "roe": "ROE",
    "revenue": "Revenue",
    "ebit": "EBIT",
    "net_income": "Net Income",
    "ebit_margin": "EBIT Margin",
    "gross_debt": "Gross Debt",
    "net_debt": "Net Debt",
    "equity": "Equity",
}

# KPIs that are typically shown as percentages
PCT_KPIS: frozenset[str] = frozenset(
    {"net_margin", "roe", "equity_to_assets", "ebit_margin"}
)

CREDIT_DEFAULT_KPIS: list[str] = [
    "credit_score",
    "fundamental_score",
    "debt_to_equity",
    "net_debt_to_cash",
    "current_ratio",
    "interest_coverage",
    "ocf_to_net_debt",
    "net_margin",
    "equity_to_assets",
    "roe",
]

EQUITY_DEFAULT_KPIS: list[str] = [
    "revenue",
    "ebit",
    "net_income",
    "net_margin",
    "ebit_margin",
    "roe",
    "equity_to_assets",
]

# All selectable KPIs (union of packs + common balance items)
ALL_KPIS: list[str] = sorted(
    set(CREDIT_DEFAULT_KPIS)
    | set(EQUITY_DEFAULT_KPIS)
    | {"qualitative_penalty", "gross_debt", "net_debt", "equity"}
)

PRIMARY_SCORE_BY_MODE: dict[ReportMode, str] = {
    "credit": "credit_score",
    "equity": "roe",
}


def default_kpis(mode: ReportMode) -> list[str]:
    if mode == "equity":
        return list(EQUITY_DEFAULT_KPIS)
    return list(CREDIT_DEFAULT_KPIS)


def kpi_label(key: str) -> str:
    return KPI_LABELS.get(key, key)


def known_industry_groups() -> list[str]:
    """Stable industry group names from the credit sector map."""
    from decifra.credit.scoring import SECTOR_TO_GROUP

    groups = sorted(set(SECTOR_TO_GROUP.values()) | {"Other"})
    return groups
