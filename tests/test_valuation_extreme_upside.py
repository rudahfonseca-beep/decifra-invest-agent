from decifra.valuation.generate import render_valuation_markdown


def test_extreme_upside_callout_in_markdown():
    md = render_valuation_markdown(
        {
            "title": "Test",
            "ticker": "FAKE3",
            "disclaimer": "Research only.",
            "dcf": {
                "wacc": 0.12,
                "wacc_source": "test",
                "cost_of_equity": 0.14,
                "after_tax_cost_of_debt": 0.08,
                "enterprise_value": 1e12,
                "net_debt": 0,
                "equity_value": 1e12,
                "value_per_share": 500.0,
                "current_price": 10.0,
                "upside_pct": 49.0,
                "years": [],
                "warnings": [],
            },
        }
    )
    assert "starting point, not a price target" in md
