from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from decifra.valuation.assumptions import DcfAssumptions
from decifra.valuation.dcf import (
    compute_cost_of_equity,
    compute_wacc,
    discount_cash_flow,
    project_fcff,
    sensitivity_grid,
)

BASE_ASSUMPTIONS = DcfAssumptions(
    forecast_years=5,
    revenue_growth_y1=0.10,
    terminal_growth=0.03,
    ebit_margin=0.20,
    tax_rate=0.30,
    da_pct_revenue=0.05,
    capex_pct_revenue=0.08,
    nwc_pct_revenue=0.02,
    risk_free_rate=0.07,
    equity_risk_premium=0.045,
    country_risk_premium=0.025,
    beta=1.2,
    cost_of_debt=0.09,
)

HIST = pd.DataFrame([{"revenue": 1000.0, "gross_debt": 400.0, "net_debt": 100.0}])
KPIS = {
    "revenue": 1000.0,
    "gross_debt": 400.0,
    "net_debt": 100.0,
    "sector": "",
    "interest_expense": None,
    "interest_coverage": None,
}
MARKET = {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": 1.2}


def test_project_fcff_growth_fades_and_terminal_capex_equals_da() -> None:
    rows = project_fcff(BASE_ASSUMPTIONS, base_revenue=1000.0)
    assert len(rows) == 5
    assert rows[0]["growth"] == pytest.approx(0.10)
    assert rows[-1]["growth"] == pytest.approx(0.03)
    # Terminal year: capex set to D&A (steady-state reinvestment)
    assert rows[-1]["capex"] == pytest.approx(rows[-1]["da"])
    # Non-terminal years use the assumed capex intensity
    assert rows[0]["capex"] == pytest.approx(rows[0]["revenue"] * 0.08)


def test_compute_wacc_matches_capm_and_weights() -> None:
    info = compute_wacc(BASE_ASSUMPTIONS, market_cap=2000.0, gross_debt=400.0)
    expected_ke = 0.07 + 1.2 * 0.045 + 0.025
    assert info["cost_of_equity"] == pytest.approx(expected_ke)
    assert compute_cost_of_equity(BASE_ASSUMPTIONS) == pytest.approx(expected_ke)
    expected_kd_at = 0.09 * (1 - 0.30)
    assert info["after_tax_cost_of_debt"] == pytest.approx(expected_kd_at)
    ew = 2000.0 / 2400.0
    dw = 400.0 / 2400.0
    assert info["equity_weight"] == pytest.approx(ew)
    assert info["debt_weight"] == pytest.approx(dw)
    assert info["wacc"] == pytest.approx(ew * expected_ke + dw * expected_kd_at)


def test_compute_wacc_override_bypasses_capm() -> None:
    a = replace(BASE_ASSUMPTIONS, wacc_override=0.11)
    info = compute_wacc(a, market_cap=2000.0, gross_debt=400.0)
    assert info["wacc"] == pytest.approx(0.11)
    assert info["source"] == "user override"


def test_discount_cash_flow_end_to_end() -> None:
    result = discount_cash_flow(
        "AAA3", BASE_ASSUMPTIONS, _hist=HIST, _kpis=KPIS, _market=MARKET
    )
    assert result.ticker == "AAA3"
    assert len(result.years) == 5
    assert result.equity_value == pytest.approx(result.enterprise_value - 100.0)
    assert result.value_per_share == pytest.approx(result.equity_value / 100.0)
    assert result.upside_pct == pytest.approx(result.value_per_share / 20.0 - 1.0)
    assert not result.warnings


def test_discount_cash_flow_clips_terminal_growth_above_wacc() -> None:
    risky = replace(BASE_ASSUMPTIONS, terminal_growth=0.50)
    result = discount_cash_flow("AAA3", risky, _hist=HIST, _kpis=KPIS, _market=MARKET)
    assert any("Terminal growth" in w for w in result.warnings)
    assert result.value_per_share is not None


def test_discount_cash_flow_missing_shares_warns() -> None:
    market_no_shares = {**MARKET, "shares_outstanding": None, "market_cap": None}
    result = discount_cash_flow(
        "AAA3", BASE_ASSUMPTIONS, _hist=HIST, _kpis=KPIS, _market=market_no_shares
    )
    assert result.value_per_share is None
    assert any("Shares outstanding" in w for w in result.warnings)
    assert result.enterprise_value != 0


def test_sensitivity_grid_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("decifra.valuation.dcf.build_annual_history", lambda t: HIST)
    monkeypatch.setattr("decifra.valuation.dcf.extract_kpis", lambda t: KPIS)
    monkeypatch.setattr("decifra.valuation.dcf.fetch_market_data", lambda t: MARKET)

    grid = sensitivity_grid("AAA3", BASE_ASSUMPTIONS)
    assert grid["metric"] == "value_per_share"
    assert len(grid["wacc_values"]) == 5
    assert len(grid["growth_values"]) == 5
    assert len(grid["grid"]) == 5
    assert all(len(row) == 5 for row in grid["grid"])
    # Center cell (no delta) should match the base result
    base = discount_cash_flow("AAA3", BASE_ASSUMPTIONS, _hist=HIST, _kpis=KPIS, _market=MARKET)
    assert grid["grid"][2][2] == pytest.approx(base.value_per_share)
