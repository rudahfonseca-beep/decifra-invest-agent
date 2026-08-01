from pathlib import Path

from decifra.schemas.alignment import align_itr_debt_dates
from decifra.schemas.assemble import assemble_valuation_waterfall, write_sample_bundle


def test_align_itr_debt():
    out = align_itr_debt_dates(
        ["2024-09-30", "2024-12-31"],
        ["2024-10-05", "2024-12-31"],
        max_days=45,
    )
    assert out["matches"][0]["aligned"] is True
    assert out["matches"][1]["debt_dt_refer"] == "2024-12-31"


def test_assemble_bundle(tmp_path, monkeypatch):
    from decifra.store import folders

    monkeypatch.setattr(folders, "COMPANIES_DIR", tmp_path / "companies")
    (tmp_path / "companies" / "PETR4").mkdir(parents=True)
    (tmp_path / "companies" / "PETR4" / "meta.json").write_text(
        '{"ticker":"PETR4","cnpj":"33000167000101","company_name":"PETROBRAS"}',
        encoding="utf-8",
    )
    paths = write_sample_bundle(tmp_path / "out", ticker="PETR4")
    assert Path(paths["company_profile.json"]).exists()
    wf = assemble_valuation_waterfall("PETR4", ocf=100, interest=20, amortization=10)
    assert wf["outputs"]["fcfe"] == 70
    assert wf["inputs"]["ocf"]["lineage"]["source_doc"]
