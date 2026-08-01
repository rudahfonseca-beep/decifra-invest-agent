from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decifra.valuation.assemble import assemble_context
from decifra.valuation.spec import ValuationSpec, validate_spec

TICKERS = ["AAA3", "BBB3"]
MARKET_MAP = {
    "AAA3": {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": None},
    "BBB3": {"price": 40.0, "shares_outstanding": 150.0, "market_cap": 6000.0, "beta": None},
}


def _row(period: str, code: str, desc: str, value: float, source: str = "DFP") -> dict:
    return {
        "DT_REFER": period,
        "CD_CONTA": code,
        "DS_CONTA": desc,
        "VL_CONTA": str(value),
        "ORDEM_EXERC": "ÚLTIMO",
        "SOURCE_DOC": source,
    }


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_company(root: Path, ticker: str, base_revenue: float) -> None:
    cdir = root / ticker
    (cdir / "financials").mkdir(parents=True)
    cdir.joinpath("meta.json").write_text(
        json.dumps({"ticker": ticker, "sector": "Energia Elétrica", "company_name": f"{ticker} SA"}),
        encoding="utf-8",
    )

    income_rows, balance_rows, cf_rows = [], [], []
    revenue = base_revenue
    for period in ("2022-12-31", "2023-12-31", "2024-12-31"):
        ebit = revenue * 0.20
        pretax = ebit - 20.0
        tax = -pretax * 0.30
        ni = pretax + tax
        income_rows += [
            _row(period, "3.01", "Receita de Venda de Bens e/ou Serviços", revenue),
            _row(period, "3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", ebit),
            _row(period, "3.06", "Resultado Financeiro", -20.0),
            _row(period, "3.06.02", "Despesas Financeiras", -20.0),
            _row(period, "3.07", "Resultado Antes dos Tributos sobre o Lucro", pretax),
            _row(period, "3.08", "Imposto de Renda e Contribuição Social sobre o Lucro", tax),
            _row(period, "3.11", "Lucro/Prejuízo Consolidado do Período", ni),
            _row(period, "3.11.01", "Atribuído a Sócios da Empresa Controladora", ni * 0.95),
        ]
        balance_rows += [
            _row(period, "1", "Ativo Total", 2000.0),
            _row(period, "1.01", "Ativo Circulante", 800.0),
            _row(period, "1.01.01", "Caixa e Equivalentes de Caixa", 300.0),
            _row(period, "1.01.02", "Aplicações Financeiras", 100.0),
            _row(period, "2", "Passivo Total", 2000.0),
            _row(period, "2.01", "Passivo Circulante", 400.0),
            _row(period, "2.03", "Patrimônio Líquido Consolidado", 1000.0),
            _row(period, "2.01.04", "Empréstimos e Financiamentos", 100.0),
            _row(period, "2.02.01", "Empréstimos e Financiamentos", 300.0),
        ]
        cf_rows += [
            _row(period, "6.01", "Caixa Líquido Atividades Operacionais", 180.0),
            _row(period, "6.01.01.04", "Depreciação, depleção e amortização", revenue * 0.05),
            _row(period, "6.01.02", "Variações nos Ativos e Passivos", -revenue * 0.02),
            _row(period, "6.02", "Caixa Líquido Atividades de Investimento", -revenue * 0.06),
            _row(period, "6.02.01", "Aquisições de ativos imobilizados e intangíveis", -revenue * 0.06),
        ]
        revenue *= 1.10

    _write_csv(cdir / "financials" / "income_statement.csv", income_rows)
    _write_csv(cdir / "financials" / "balance_sheet.csv", balance_rows)
    _write_csv(cdir / "financials" / "cash_flow.csv", cf_rows)


@pytest.fixture
def two_companies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("decifra.valuation.historical.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.metrics.load_meta",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        "decifra.valuation.multiples.load_meta",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )

    for ticker, base_revenue in (("AAA3", 1000.0), ("BBB3", 1500.0)):
        _write_company(tmp_path, ticker, base_revenue)

    fake_market = lambda t: MARKET_MAP[t.upper()]  # noqa: E731
    monkeypatch.setattr("decifra.valuation.assumptions.fetch_market_data", fake_market)
    monkeypatch.setattr("decifra.valuation.assumptions.compute_regression_beta", lambda t, **kw: (None, 0))
    monkeypatch.setattr("decifra.valuation.dcf.fetch_market_data", fake_market)
    monkeypatch.setattr("decifra.valuation.multiples.fetch_market_data", fake_market)
    return tmp_path


def test_assemble_context_dcf_only(two_companies: Path) -> None:
    spec = validate_spec(ValuationSpec(ticker="AAA3"), known_tickers=TICKERS)
    ctx = assemble_context(spec)
    assert ctx["ticker"] == "AAA3"
    assert ctx["multiples"] is None
    assert ctx["dcf"]["ticker"] == "AAA3"
    assert len(ctx["dcf"]["years"]) == spec.forecast_years
    assert ctx["sensitivity"]["grid"]
    assert any(n["key"] == "revenue_growth_y1" for n in ctx["methodology"])


def test_assemble_context_with_comparatives(two_companies: Path) -> None:
    spec = validate_spec(
        ValuationSpec(ticker="AAA3", comparatives=["BBB3"]), known_tickers=TICKERS
    )
    ctx = assemble_context(spec)
    assert ctx["multiples"] is not None
    assert ctx["multiples"]["peer_count"] == 1
    assert ctx["comparatives"] == ["BBB3"]


def test_assemble_context_applies_user_overrides(two_companies: Path) -> None:
    spec = validate_spec(
        ValuationSpec(ticker="AAA3", dcf_assumptions={"terminal_growth": 0.02, "beta": 1.5}),
        known_tickers=TICKERS,
    )
    ctx = assemble_context(spec)
    assert ctx["dcf"]["assumptions"]["beta"] == pytest.approx(1.5)
    override_notes = [n for n in ctx["methodology"] if n["formula"] == "user override"]
    assert {n["key"] for n in override_notes} == {"terminal_growth", "beta"}
