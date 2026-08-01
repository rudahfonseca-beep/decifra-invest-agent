from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decifra.valuation.assumptions import build_default_assumptions


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


@pytest.fixture
def company_with_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("decifra.valuation.historical.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.metrics.load_meta",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )

    root = tmp_path / "AAA3"
    (root / "financials").mkdir(parents=True)
    (root / "meta.json").write_text(
        json.dumps({"ticker": "AAA3", "sector": "Energia Elétrica", "company_name": "AAA3 SA"}),
        encoding="utf-8",
    )

    income_rows, balance_rows, cf_rows = [], [], []
    # Steady 10% revenue growth, 20% EBIT margin, 30% effective tax rate, 5% debt cost
    for period, revenue in (("2022-12-31", 1000.0), ("2023-12-31", 1100.0), ("2024-12-31", 1210.0)):
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

    _write_csv(root / "financials" / "income_statement.csv", income_rows)
    _write_csv(root / "financials" / "balance_sheet.csv", balance_rows)
    _write_csv(root / "financials" / "cash_flow.csv", cf_rows)
    return root


def test_default_assumptions_use_own_history(
    company_with_history: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "decifra.valuation.assumptions.fetch_market_data",
        lambda t: {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": None},
    )
    monkeypatch.setattr(
        "decifra.valuation.assumptions.compute_regression_beta", lambda t, **kw: (None, 0)
    )

    assumptions, notes = build_default_assumptions("AAA3")

    assert assumptions.revenue_growth_y1 == pytest.approx(0.10, abs=1e-6)
    assert assumptions.ebit_margin == pytest.approx(0.20, abs=1e-6)
    assert assumptions.tax_rate == pytest.approx(0.30, abs=1e-6)
    assert assumptions.da_pct_revenue == pytest.approx(0.05, abs=1e-6)
    assert assumptions.capex_pct_revenue == pytest.approx(0.06, abs=1e-6)
    assert assumptions.nwc_pct_revenue == pytest.approx(0.02, abs=1e-6)
    # No market beta, no local price history, no peers -> neutral default
    assert assumptions.beta == pytest.approx(1.0)

    note_keys = {n.key for n in notes}
    assert {"revenue_growth_y1", "ebit_margin", "tax_rate", "beta", "cost_of_debt"} <= note_keys
    beta_note = next(n for n in notes if n.key == "beta")
    assert "neutral" in beta_note.rationale.lower()


def test_beta_prefers_market_data_when_sane(
    company_with_history: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "decifra.valuation.assumptions.fetch_market_data",
        lambda t: {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": 1.35},
    )
    monkeypatch.setattr(
        "decifra.valuation.assumptions.compute_regression_beta", lambda t, **kw: (None, 0)
    )
    assumptions, notes = build_default_assumptions("AAA3")
    assert assumptions.beta == pytest.approx(1.35)
    beta_note = next(n for n in notes if n.key == "beta")
    assert "yfinance" in beta_note.formula


def test_cost_of_debt_uses_own_effective_rate(
    company_with_history: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "decifra.valuation.assumptions.fetch_market_data",
        lambda t: {"price": 20.0, "shares_outstanding": 100.0, "market_cap": 2000.0, "beta": 1.0},
    )
    monkeypatch.setattr(
        "decifra.valuation.assumptions.compute_regression_beta", lambda t, **kw: (None, 0)
    )
    assumptions, notes = build_default_assumptions("AAA3")
    # interest_expense=-20, gross_debt=400 -> own effective rate = 20/400 = 5%
    assert assumptions.cost_of_debt == pytest.approx(0.05, abs=1e-6)
    kd_note = next(n for n in notes if n.key == "cost_of_debt")
    assert "own effective rate" in kd_note.formula
