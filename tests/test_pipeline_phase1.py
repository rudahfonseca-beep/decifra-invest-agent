"""Phase 1 ingestion: FRE extracts, ANBIMA debt, B3 shares/Balcão."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from decifra.anbima.debt import normalize_anbima_frame, sync_anbima, write_sample_fixture
from decifra.b3.balcao import sync_b3_bonds, write_sample_balcao
from decifra.b3.shares import sync_b3_shares
from decifra.cvm.fre import extract_company_fre, load_fre_frames, write_company_fre
from decifra.http_util import normalize_cnpj


def test_fre_extract_and_write(tmp_path, monkeypatch):
    from decifra import config
    from decifra.store import folders

    monkeypatch.setattr(config, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(folders, "COMPANIES_DIR", tmp_path / "companies")

    df = pd.DataFrame(
        {
            "CNPJ_CIA": ["33.000.167/0001-01"],
            "DENOM_CIA": ["PETROBRAS"],
            "DT_REFER": ["2024-12-31"],
            "CNPJ_NORM": [normalize_cnpj("33.000.167/0001-01")],
            "SOURCE_DOC": ["FRE"],
        }
    )
    subset = extract_company_fre(df, "33000167000101")
    assert len(subset) == 1
    path = write_company_fre("PETR4", subset, year=2024)
    assert path is not None
    assert path.exists()


def test_fre_load_from_zip(tmp_path):
    zpath = tmp_path / "fre_cia_aberta_2024.zip"
    csv_name = "fre_cia_aberta_2024.csv"
    body = "CNPJ_CIA;DENOM_CIA;DT_REFER\n33.000.167/0001-01;PETROBRAS;2024-12-31\n"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr(csv_name, body)
    df = load_fre_frames(zpath)
    assert not df.empty
    assert df.iloc[0]["CNPJ_NORM"] == "33000167000101"
    assert df.iloc[0]["SOURCE_DOC"] == "FRE"


def test_anbima_normalize_and_sync(tmp_path, monkeypatch):
    from decifra import config
    from decifra.store import folders

    monkeypatch.setattr(config, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(config, "ANBIMA_CACHE_DIR", tmp_path / "cache" / "anbima")
    monkeypatch.setattr(config, "UNIVERSE_DIR", tmp_path / "universe")
    monkeypatch.setattr(folders, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(folders, "IBOVESPA_JSON", tmp_path / "universe" / "ibovespa.json")

    (tmp_path / "universe").mkdir(parents=True)
    (tmp_path / "universe" / "ibovespa.json").write_text(
        '{"constituents":[{"ticker":"PETR4","cnpj":"33000167000101"}]}',
        encoding="utf-8",
    )
    meta_dir = tmp_path / "companies" / "PETR4"
    meta_dir.mkdir(parents=True)
    (meta_dir / "meta.json").write_text(
        '{"ticker":"PETR4","cnpj":"33000167000101"}', encoding="utf-8"
    )

    fixture = write_sample_fixture(tmp_path / "cache" / "anbima" / "debt_instruments.csv")
    raw = pd.read_csv(fixture, dtype=str)
    norm = normalize_anbima_frame(raw)
    assert "CDI+" in set(norm["indexer"]) or "IPCA+" in set(norm["indexer"])

    result = sync_anbima(ticker="PETR4", source_path=fixture, write_fixture_if_missing=False)
    assert "PETR4" in result["written"]
    assert (tmp_path / "companies" / "PETR4" / "debt" / "anbima_instruments.csv").exists()


def test_b3_shares_and_balcao(tmp_path, monkeypatch):
    from decifra import config
    from decifra.store import folders

    monkeypatch.setattr(config, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(config, "UNIVERSE_DIR", tmp_path / "universe")
    monkeypatch.setattr(config, "B3_SHARES_JSON", tmp_path / "universe" / "b3_shares.json")
    monkeypatch.setattr(config, "B3_BALCAO_JSON", tmp_path / "universe" / "b3_balcao_bonds.json")
    monkeypatch.setattr(folders, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(folders, "IBOVESPA_JSON", tmp_path / "universe" / "ibovespa.json")

    (tmp_path / "universe").mkdir(parents=True)
    (tmp_path / "universe" / "ibovespa.json").write_text(
        '{"constituents":[{"ticker":"PETR4","cnpj":"33000167000101","part_pct":10.0}]}',
        encoding="utf-8",
    )
    meta_dir = tmp_path / "companies" / "PETR4"
    meta_dir.mkdir(parents=True)
    (meta_dir / "meta.json").write_text(
        '{"ticker":"PETR4","cnpj":"33000167000101"}', encoding="utf-8"
    )

    # Re-import modules that captured paths — call via patched config attributes
    import decifra.b3.shares as shares_mod
    import decifra.b3.balcao as balcao_mod

    monkeypatch.setattr(shares_mod, "B3_SHARES_JSON", tmp_path / "universe" / "b3_shares.json")
    monkeypatch.setattr(balcao_mod, "B3_BALCAO_JSON", tmp_path / "universe" / "b3_balcao_bonds.json")

    r1 = sync_b3_shares(ticker="PETR4", force=True)
    assert "PETR4" in r1["updated"]
    assert (tmp_path / "universe" / "b3_shares.json").exists()

    balc = write_sample_balcao(tmp_path / "cache" / "b3" / "balcao_bonds.csv")
    r2 = sync_b3_bonds(ticker="PETR4", source_path=balc, write_fixture_if_missing=False)
    assert "PETR4" in r2["written"]
