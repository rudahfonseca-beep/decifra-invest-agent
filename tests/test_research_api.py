from decifra.schemas.api_server import handle_api, handle_api_post
from decifra.schemas.research_api import industries_payload, tickers_payload


def test_industries_and_tickers_shape():
    ind = industries_payload(include_signals=False)
    assert "industries" in ind
    assert isinstance(ind["industries"], list)
    tix = tickers_payload(include_signals=False, show_incomplete=True)
    assert "tickers" in tix
    assert "count" in tix


def test_api_routes_credit_industries_tickers():
    for path in ("/api/industries", "/api/tickers", "/api/credit", "/api/coverage", "/api/report/catalog"):
        code, payload = handle_api(path, {})
        assert code == 200, path
        assert isinstance(payload, dict)


def test_sync_financials_post_validation():
    code, payload = handle_api_post("/api/sync/financials", {})
    assert code == 400
    assert "tickers" in payload["error"]

    code, payload = handle_api_post(
        "/api/sync/financials", {"tickers": ["PETR4"], "year_from": 1990, "year_to": 2020}
    )
    assert code == 400
    assert "years" in payload["error"]
