from __future__ import annotations

import json
from pathlib import Path

import pytest

from decifra.valuation.spec import (
    SpecValidationError,
    ValuationSpec,
    load_spec,
    validate_spec,
)

KNOWN = ["AAA3", "BBB3", "CCC3"]


def test_validate_requires_ticker() -> None:
    with pytest.raises(SpecValidationError, match="subject ticker"):
        validate_spec(ValuationSpec(ticker=""), known_tickers=KNOWN)


def test_validate_unknown_ticker() -> None:
    with pytest.raises(SpecValidationError, match="Unknown ticker"):
        validate_spec(ValuationSpec(ticker="ZZZZ9"), known_tickers=KNOWN)


def test_validate_removes_self_and_dedupes_comparatives() -> None:
    spec = validate_spec(
        ValuationSpec(ticker="aaa3", comparatives=["AAA3", "BBB3", "bbb3", "CCC3"]),
        known_tickers=KNOWN,
    )
    assert spec.ticker == "aaa3"
    assert spec.comparatives == ["BBB3", "CCC3"]


def test_validate_unknown_comparative() -> None:
    with pytest.raises(SpecValidationError, match="Unknown comparative"):
        validate_spec(ValuationSpec(ticker="AAA3", comparatives=["ZZZZ9"]), known_tickers=KNOWN)


def test_validate_invalid_stat() -> None:
    with pytest.raises(SpecValidationError, match="multiples_stat"):
        validate_spec(ValuationSpec(ticker="AAA3", multiples_stat="mode"), known_tickers=KNOWN)


def test_validate_forecast_years_bounds() -> None:
    with pytest.raises(SpecValidationError, match="forecast_years"):
        validate_spec(ValuationSpec(ticker="AAA3", forecast_years=1), known_tickers=KNOWN)
    with pytest.raises(SpecValidationError, match="forecast_years"):
        validate_spec(ValuationSpec(ticker="AAA3", forecast_years=11), known_tickers=KNOWN)


def test_validate_unknown_assumption_key() -> None:
    with pytest.raises(SpecValidationError, match="Unknown dcf_assumptions"):
        validate_spec(
            ValuationSpec(ticker="AAA3", dcf_assumptions={"not_a_real_field": 1}),
            known_tickers=KNOWN,
        )


def test_validate_accepts_known_assumption_keys() -> None:
    spec = validate_spec(
        ValuationSpec(ticker="AAA3", dcf_assumptions={"terminal_growth": 0.03, "beta": 1.1}),
        known_tickers=KNOWN,
    )
    assert spec.dcf_assumptions == {"terminal_growth": 0.03, "beta": 1.1}


def test_load_spec_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("decifra.valuation.spec.list_tickers", lambda: KNOWN)
    path = tmp_path / "spec.json"
    path.write_text(
        json.dumps({"ticker": "aaa3", "comparatives": ["bbb3"], "multiples_stat": "mean"}),
        encoding="utf-8",
    )
    spec = load_spec(path)
    assert spec.ticker == "AAA3"
    assert spec.comparatives == ["BBB3"]
    assert spec.multiples_stat == "mean"


def test_default_title() -> None:
    spec = ValuationSpec(ticker="AAA3", comparatives=["BBB3", "CCC3"])
    assert spec.default_title() == "Valuation — AAA3 vs BBB3, CCC3"
    assert ValuationSpec(ticker="AAA3", title="Custom").default_title() == "Custom"
