from decifra.credit.capacity import evaluate_capacity
from decifra.credit.merton import merton_dtd
from decifra.valuation.apv import compute_apv
from decifra.valuation.waterfall import ocf_to_fcfe_waterfall


def test_apv_basic():
    r = compute_apv(
        unlevered_fcff=[100.0, 110.0, 120.0],
        unlevered_cost_of_capital=0.10,
        debt_interest=[40.0, 40.0, 40.0],
        tax_rate=0.34,
        distress_cost_pv=5.0,
    )
    assert r.v_u > 0
    assert r.pv_tax_shield > 0
    assert r.v_l == r.v_u + r.pv_tax_shield - 5.0


def test_waterfall_and_capacity():
    w = ocf_to_fcfe_waterfall(ocf=200, interest=50, mandatory_amortization=30)
    assert w.debt_service == 80
    assert w.fcfe == 120
    assert w.covered is True
    c = evaluate_capacity(net_debt=700, ebitda=100, ocf_or_ebitda_proxy=200, debt_service=80)
    assert c.net_debt_ebitda.breach is True  # 7.0 > 3.5
    assert c.dscr.breach is False  # 2.5 >= 1.25
    assert c.any_breach is True


def test_merton_dtd():
    r = merton_dtd(asset_value=100, debt_face=80, risk_free=0.05, horizon_years=1.0, asset_vol=0.25)
    assert r.equity_value > 0
    assert r.debt_value > 0
    assert 0 <= r.default_probability <= 1
