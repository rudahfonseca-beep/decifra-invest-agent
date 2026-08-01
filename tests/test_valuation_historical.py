from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from decifra.valuation.historical import build_annual_history, cagr, trailing_average, trailing_median


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
def three_year_history(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr("decifra.valuation.historical.company_dir", lambda t: tmp_path / t.upper())
    root = tmp_path / "AAA3" / "financials"

    income_rows = []
    balance_rows = []
    cf_rows = []
    # Revenue grows 1000 -> 1100 -> 1210 (10% CAGR); EBIT margin steady at 20%
    for period, revenue, ebit, pretax, tax, ni, ni_ctrl in (
        ("2022-12-31", 1000.0, 200.0, 180.0, -54.0, 126.0, 120.0),
        ("2023-12-31", 1100.0, 220.0, 198.0, -59.4, 138.6, 132.0),
        ("2024-12-31", 1210.0, 242.0, 217.8, -65.34, 152.46, 145.2),
    ):
        income_rows += [
            _row(period, "3.01", "Receita de Venda de Bens e/ou Serviços", revenue),
            _row(period, "3.05", "Resultado Antes do Resultado Financeiro e dos Tributos", ebit),
            _row(period, "3.06", "Resultado Financeiro", -20.0),
            _row(period, "3.07", "Resultado Antes dos Tributos sobre o Lucro", pretax),
            _row(period, "3.08", "Imposto de Renda e Contribuição Social sobre o Lucro", tax),
            _row(period, "3.11", "Lucro/Prejuízo Consolidado do Período", ni),
            _row(period, "3.11.01", "Atribuído a Sócios da Empresa Controladora", ni_ctrl),
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
            _row(period, "6.02", "Caixa Líquido Atividades de Investimento", -revenue * 0.08),
            _row(period, "6.02.01", "Aquisições de ativos imobilizados e intangíveis", -revenue * 0.08),
        ]

    _write_csv(root / "income_statement.csv", income_rows)
    _write_csv(root / "balance_sheet.csv", balance_rows)
    _write_csv(root / "cash_flow.csv", cf_rows)
    return root


def test_build_annual_history_shape(three_year_history: Path) -> None:
    hist = build_annual_history("AAA3")
    assert list(hist["period"]) == ["2022-12-31", "2023-12-31", "2024-12-31"]
    assert hist.loc[2, "revenue"] == pytest.approx(1210.0)
    assert hist.loc[2, "gross_debt"] == pytest.approx(400.0)
    assert hist.loc[2, "net_debt"] == pytest.approx(0.0)


def test_build_annual_history_ratios(three_year_history: Path) -> None:
    hist = build_annual_history("AAA3")
    # EBIT margin steady at 20% every year
    assert hist["ebit_margin"].round(2).tolist() == [0.2, 0.2, 0.2]
    # Revenue growth: first year NaN, then 10% each year
    assert pd.isna(hist["revenue_growth"].iloc[0])
    assert hist["revenue_growth"].iloc[1] == pytest.approx(0.10, abs=1e-6)
    assert hist["revenue_growth"].iloc[2] == pytest.approx(0.10, abs=1e-6)
    # Effective tax rate ~30% every year
    assert hist["effective_tax_rate"].round(2).tolist() == [0.3, 0.3, 0.3]
    # Capex/D&A intensity as % revenue
    assert hist["da_pct_revenue"].round(2).tolist() == [0.05, 0.05, 0.05]
    assert hist["capex_pct_revenue"].round(2).tolist() == [0.08, 0.08, 0.08]
    assert hist["nwc_pct_revenue"].round(2).tolist() == [0.02, 0.02, 0.02]


def test_cagr_and_trailing_stats(three_year_history: Path) -> None:
    hist = build_annual_history("AAA3")
    assert cagr(hist, "revenue", 2) == pytest.approx(0.10, abs=1e-6)
    assert trailing_average(hist, "ebit_margin", 3) == pytest.approx(0.20, abs=1e-6)
    assert trailing_median(hist, "ebit_margin", 3) == pytest.approx(0.20, abs=1e-6)


def test_mil_scale_normalized_to_absolute_reais(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CVM reports monetary accounts in thousands (ESCALA_MOEDA=MIL); historical.py
    must scale to absolute reais so valuation can safely combine these figures
    with market data (price x shares), which is already in absolute reais."""
    monkeypatch.setattr("decifra.valuation.historical.company_dir", lambda t: tmp_path / t.upper())
    root = tmp_path / "BBB3" / "financials"

    def _mil_row(code: str, desc: str, value: float) -> dict:
        row = _row("2024-12-31", code, desc, value)
        row["ESCALA_MOEDA"] = "MIL"
        return row

    _write_csv(
        root / "income_statement.csv",
        [_mil_row("3.01", "Receita de Venda de Bens e/ou Serviços", 490829.0)],
    )

    hist = build_annual_history("BBB3")
    # 490,829 thousand reais -> 490,829,000 absolute reais
    assert hist.loc[0, "revenue"] == pytest.approx(490_829_000.0)


def test_empty_history_when_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("decifra.valuation.historical.company_dir", lambda t: tmp_path / t.upper())
    hist = build_annual_history("ZZZ9")
    assert hist.empty
    assert cagr(hist, "revenue", 3) is None
