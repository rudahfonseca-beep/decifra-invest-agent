from __future__ import annotations

from statistics import mean, median

import pandas as pd
import pytest

from decifra.valuation.multiples import compute_multiples, relative_valuation

HIST_MAP: dict[str, pd.DataFrame] = {
    "AAA3": pd.DataFrame(
        [
            {
                "revenue": 1000.0,
                "ebit": 200.0,
                "depreciation_amortization": 50.0,
                "net_income_controllers": 120.0,
                "equity": 800.0,
                "gross_debt": 400.0,
                "net_debt": 300.0,
            }
        ]
    ),
    "BBB3": pd.DataFrame(
        [
            {
                "revenue": 2000.0,
                "ebit": 300.0,
                "depreciation_amortization": 100.0,
                "net_income_controllers": 150.0,
                "equity": 1200.0,
                "gross_debt": 500.0,
                "net_debt": 350.0,
            }
        ]
    ),
    "CCC3": pd.DataFrame(
        [
            {
                "revenue": 1500.0,
                "ebit": 250.0,
                "depreciation_amortization": 80.0,
                "net_income_controllers": 140.0,
                "equity": 900.0,
                "gross_debt": 300.0,
                "net_debt": 200.0,
            }
        ]
    ),
}
MARKET_MAP = {
    "AAA3": {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": 1.0},
    "BBB3": {"price": 40.0, "shares_outstanding": 150.0, "market_cap": 6000.0, "beta": 1.0},
    "CCC3": {"price": 30.0, "shares_outstanding": 120.0, "market_cap": 3600.0, "beta": 1.0},
}


@pytest.fixture(autouse=True)
def patch_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("decifra.valuation.multiples.build_annual_history", lambda t: HIST_MAP[t.upper()])
    monkeypatch.setattr("decifra.valuation.multiples.fetch_market_data", lambda t: MARKET_MAP[t.upper()])
    monkeypatch.setattr(
        "decifra.valuation.multiples.load_identity", lambda t: {"company_name": f"{t.upper()} SA"}
    )


def test_compute_multiples_aaa3() -> None:
    m = compute_multiples("AAA3")
    assert m.market_cap == pytest.approx(2000.0)
    assert m.enterprise_value == pytest.approx(2300.0)  # market_cap + net_debt
    assert m.ebitda == pytest.approx(250.0)  # ebit + D&A
    assert m.pe == pytest.approx(2000.0 / 120.0)
    assert m.ev_ebitda == pytest.approx(2300.0 / 250.0)
    assert m.ev_revenue == pytest.approx(2300.0 / 1000.0)
    assert m.ev_ebit == pytest.approx(2300.0 / 200.0)
    assert m.pb == pytest.approx(2000.0 / 800.0)
    assert not m.warnings


def test_compute_multiples_handles_negative_net_income(monkeypatch: pytest.MonkeyPatch) -> None:
    hist = pd.DataFrame(
        [{"revenue": 1000.0, "ebit": -50.0, "depreciation_amortization": 50.0, "net_income_controllers": -80.0, "equity": 500.0, "gross_debt": 200.0, "net_debt": 150.0}]
    )
    monkeypatch.setattr("decifra.valuation.multiples.build_annual_history", lambda t: hist)
    m = compute_multiples("AAA3")
    assert m.pe is None
    assert m.ev_ebit is None
    assert any("Net income is zero/negative" in w for w in m.warnings)


def test_relative_valuation_median_matches_manual_calc() -> None:
    result = relative_valuation("AAA3", ["BBB3", "CCC3"], stat="median")
    bbb = compute_multiples("BBB3")
    ccc = compute_multiples("CCC3")

    assert result.peer_count == 2
    assert result.peer_benchmark is True
    assert result.peer_multiples["pe"] == pytest.approx(median([bbb.pe, ccc.pe]))
    assert result.peer_multiples["ev_ebitda"] == pytest.approx(median([bbb.ev_ebitda, ccc.ev_ebitda]))
    assert result.peer_multiples["pb"] == pytest.approx(median([bbb.pb, ccc.pb]))

    subject = result.subject
    expected_pe_price = (result.peer_multiples["pe"] * subject.net_income) / subject.shares_outstanding
    assert result.implied_price["pe"] == pytest.approx(expected_pe_price)

    expected_ev_ebitda_price = (
        result.peer_multiples["ev_ebitda"] * subject.ebitda - subject.net_debt
    ) / subject.shares_outstanding
    assert result.implied_price["ev_ebitda"] == pytest.approx(expected_ev_ebitda_price)

    assert result.implied_price_low is not None
    assert result.implied_price_high is not None
    assert result.implied_price_low <= result.implied_price_avg <= result.implied_price_high


def test_relative_valuation_mean_stat() -> None:
    result = relative_valuation("AAA3", ["BBB3", "CCC3"], stat="mean")
    bbb = compute_multiples("BBB3")
    ccc = compute_multiples("CCC3")
    assert result.peer_multiples["pb"] == pytest.approx(mean([bbb.pb, ccc.pb]))


def test_relative_valuation_single_peer_flags_insufficient_benchmark() -> None:
    result = relative_valuation("AAA3", ["BBB3"], stat="median")
    assert result.peer_count == 1
    assert result.peer_benchmark is False
    assert any("Only 1 comparable" in w for w in result.warnings)


def test_relative_valuation_rejects_unknown_stat() -> None:
    with pytest.raises(ValueError):
        relative_valuation("AAA3", ["BBB3"], stat="mode")
