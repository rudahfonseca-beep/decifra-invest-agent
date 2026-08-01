"""IMP-036/038: ticker assemblers + screener (formula + mocked lake)."""

from __future__ import annotations

from decifra.credit.assemble_models import assemble_capacity
from decifra.schemas.api_server import handle_api
from decifra.schemas.screener import _signal
from decifra.valuation.apv import compute_apv
from decifra.valuation.market_data import _eps_implied_shares


def test_eps_implied_shares_from_mcap_price():
    shares, how = _eps_implied_shares(
        price=10.0, market_cap=1000.0, trailing_eps=None, net_income=None
    )
    assert shares == 100.0
    assert how == "market_cap/price"


def test_eps_implied_shares_from_ni_eps():
    shares, how = _eps_implied_shares(
        price=None, market_cap=None, trailing_eps=2.0, net_income=200.0
    )
    assert shares == 100.0
    assert how == "net_income/EPS"


def test_signal_mapping():
    assert _signal(apv_discount_pct=0.2, nd_ebitda=1.0, dscr=2.0, merton_pd=0.01, any_breach=False) == "safe"
    assert _signal(apv_discount_pct=-0.1, nd_ebitda=1.0, dscr=2.0, merton_pd=0.01, any_breach=False) == "warning"
    assert _signal(apv_discount_pct=0.1, nd_ebitda=1.0, dscr=0.5, merton_pd=0.01, any_breach=False) == "distress"
    assert _signal(apv_discount_pct=0.1, nd_ebitda=1.0, dscr=2.0, merton_pd=0.15, any_breach=False) == "distress"


def test_api_health():
    code, payload = handle_api("/api/health", {})
    assert code == 200
    assert payload["ok"] is True


def test_assemble_capacity_petr4_smoke():
    """Uses local lake when present; otherwise still returns structure."""
    pack = assemble_capacity("PETR4")
    assert pack["ticker"] == "PETR4"
    assert "capacity" in pack
    assert "net_debt_ebitda" in pack["capacity"]


def test_apv_still_formula():
    r = compute_apv(
        unlevered_fcff=[100.0, 110.0],
        unlevered_cost_of_capital=0.1,
        debt_interest=[20.0, 20.0],
    )
    assert r.v_l > 0
