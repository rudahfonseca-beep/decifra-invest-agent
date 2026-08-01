from decifra.funds.cvm import sync_cvm_funds
from decifra.funds.edgar import sync_edgar


def test_funds_and_edgar(tmp_path, monkeypatch):
    import decifra.funds.cvm as cvm_mod
    import decifra.funds.edgar as edgar_mod
    from decifra import config

    monkeypatch.setattr(config, "FUNDS_DIR", tmp_path / "funds")
    monkeypatch.setattr(config, "CVM_CACHE_DIR", tmp_path / "cache" / "cvm")
    monkeypatch.setattr(cvm_mod, "FUNDS_DIR", tmp_path / "funds")
    monkeypatch.setattr(cvm_mod, "CVM_CACHE_DIR", tmp_path / "cache" / "cvm")
    monkeypatch.setattr(edgar_mod, "FUNDS_DIR", tmp_path / "funds")

    r = sync_cvm_funds(year=2026, month=7, from_cache_only=True)
    assert r["written"]
    assert (tmp_path / "funds" / "202607" / "inf_diario.csv").exists()

    e = sync_edgar(use_network=False)
    assert e["count"] >= 1
    assert (tmp_path / "funds" / "edgar" / "exposure.json").exists()
