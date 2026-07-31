from __future__ import annotations

import json
from pathlib import Path

import pytest

from decifra.report.spec import (
    EntitySelection,
    ReportSpec,
    SpecValidationError,
    load_spec,
    validate_spec,
)


KNOWN = ["AAA3", "BBB3", "CCC3"]
INDUSTRIES = ["Energy", "Oil & Gas", "Other"]


def test_validate_requires_subjects() -> None:
    with pytest.raises(SpecValidationError, match="Subjects"):
        validate_spec(
            ReportSpec(mode="credit", subjects=EntitySelection()),
            known_tickers=KNOWN,
            known_industries=INDUSTRIES,
        )


def test_validate_unknown_ticker() -> None:
    with pytest.raises(SpecValidationError, match="Unknown ticker"):
        validate_spec(
            ReportSpec(
                mode="credit",
                subjects=EntitySelection(companies=["ZZZZ9"]),
            ),
            known_tickers=KNOWN,
            known_industries=INDUSTRIES,
        )


def test_validate_unknown_industry() -> None:
    with pytest.raises(SpecValidationError, match="Unknown industry"):
        validate_spec(
            ReportSpec(
                mode="credit",
                subjects=EntitySelection(industries=["Moon Mining"]),
            ),
            known_tickers=KNOWN,
            known_industries=INDUSTRIES,
        )


def test_validate_unknown_kpi() -> None:
    with pytest.raises(SpecValidationError, match="Unknown KPI"):
        validate_spec(
            ReportSpec(
                mode="credit",
                subjects=EntitySelection(companies=["AAA3"]),
                kpis=["not_a_real_kpi"],
            ),
            known_tickers=KNOWN,
            known_industries=INDUSTRIES,
        )


def test_validate_ok_and_defaults() -> None:
    spec = validate_spec(
        ReportSpec(
            mode="equity",
            subjects=EntitySelection(companies=["aaa3"], industries=["energy"]),
            comparatives=EntitySelection(companies=["BBB3"]),
            kpis=[],
        ),
        known_tickers=KNOWN,
        known_industries=INDUSTRIES,
    )
    assert spec.subjects.companies == ["AAA3"]
    assert spec.subjects.industries == ["Energy"]
    assert "roe" in spec.resolved_kpis()
    assert "Credit" not in spec.default_title()
    assert "Equity" in spec.default_title()


def test_load_spec_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "decifra.report.spec.list_tickers",
        lambda: KNOWN,
    )
    monkeypatch.setattr(
        "decifra.report.catalog.known_industry_groups",
        lambda: INDUSTRIES,
    )
    # load_spec calls validate_spec which uses list_tickers / known_industry_groups
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps(
            {
                "mode": "credit",
                "subjects": {"companies": ["AAA3"], "industries": []},
                "kpis": ["debt_to_equity", "credit_score"],
                "language": "en",
            }
        ),
        encoding="utf-8",
    )
    # Patch known industries via validate path — load_spec uses known_industry_groups
    monkeypatch.setattr(
        "decifra.report.spec.known_industry_groups",
        lambda: INDUSTRIES,
    )
    spec = load_spec(path)
    assert spec.mode == "credit"
    assert spec.language == "en"
    assert spec.kpis == ["debt_to_equity", "credit_score"]


def test_invalid_mode_from_dict() -> None:
    with pytest.raises(ValueError, match="Invalid mode"):
        ReportSpec.from_dict({"mode": "macro", "subjects": {"companies": ["AAA3"]}})
