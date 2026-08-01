from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decifra.credit.metrics import extract_kpis, _filter_latest_dfp
from decifra.credit.scoring import (
    _percentile_rank,
    build_credit_table,
    industry_group,
)
from decifra.credit.signals import scan_qualitative_signals


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)


def _company_tree(root: Path, ticker: str, sector: str = "Energia Elétrica") -> Path:
    cdir = root / ticker
    (cdir / "financials").mkdir(parents=True)
    (cdir / "notices" / "pdfs").mkdir(parents=True)
    (cdir / "transcripts" / "text").mkdir(parents=True)
    meta = {
        "ticker": ticker,
        "company_name": f"{ticker} SA",
        "stock_name": ticker,
        "sector": sector,
        "cnpj": "12345678000199",
    }
    (cdir / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return cdir


def _statement_rows(
    *,
    period: str = "2024-12-31",
    accounts: dict[str, tuple[str, float]],
    source: str = "DFP",
) -> list[dict]:
    rows = []
    for code, (desc, val) in accounts.items():
        rows.append(
            {
                "DT_REFER": period,
                "CD_CONTA": code,
                "DS_CONTA": desc,
                "VL_CONTA": str(val),
                "ESCALA_MOEDA": "MIL",
                "SOURCE_DOC": source,
                "ORDEM_EXERC": "ÚLTIMO",
            }
        )
        # Penúltimo noise row
        rows.append(
            {
                "DT_REFER": period,
                "CD_CONTA": code,
                "DS_CONTA": desc,
                "VL_CONTA": str(val * 0.5),
                "ESCALA_MOEDA": "MIL",
                "SOURCE_DOC": source,
                "ORDEM_EXERC": "PENÚLTIMO",
            }
        )
    return rows


@pytest.fixture
def credit_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Three Energy peers with different leverage for percentile tests."""
    monkeypatch.setattr("decifra.store.folders.COMPANIES_DIR", tmp_path)
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.signals.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.scoring.list_tickers", lambda t=None: ["AAA3", "BBB3", "CCC3"] if not t else [t.upper()])
    monkeypatch.setattr(
        "decifra.credit.scoring.load_universe",
        lambda: {"constituents": []},
    )
    monkeypatch.setattr(
        "decifra.credit.metrics.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        "decifra.credit.scoring.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )

    # AAA3: low debt / strong
    a = _company_tree(tmp_path, "AAA3", "Energia Elétrica")
    _write_csv(
        a / "financials" / "income_statement.csv",
        _statement_rows(
            accounts={
                "3.01": ("Receita de Venda", 1000),
                "3.05": ("Resultado Antes do Resultado Financeiro", 200),
                "3.06": ("Resultado Financeiro", -20),
                "3.11": ("Lucro/Prejuízo Consolidado do Período", 100),
            }
        ),
    )
    _write_csv(
        a / "financials" / "balance_sheet.csv",
        _statement_rows(
            accounts={
                "1": ("Ativo Total", 2000),
                "1.01": ("Ativo Circulante", 800),
                "1.01.01": ("Caixa e Equivalentes de Caixa", 300),
                "1.01.02": ("Aplicações Financeiras", 100),
                "2": ("Passivo Total", 2000),
                "2.01": ("Passivo Circulante", 400),
                "2.03": ("Patrimônio Líquido Consolidado", 1000),
                "2.01.04": ("Empréstimos e Financiamentos", 50),
                "2.02.01": ("Empréstimos e Financiamentos", 50),
            }
        ),
    )
    _write_csv(
        a / "financials" / "cash_flow.csv",
        _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 150)}),
    )

    # BBB3: mid
    b = _company_tree(tmp_path, "BBB3", "Energia Elétrica")
    _write_csv(
        b / "financials" / "income_statement.csv",
        _statement_rows(
            accounts={
                "3.01": ("Receita de Venda", 1000),
                "3.05": ("Resultado Antes do Resultado Financeiro", 150),
                "3.06": ("Resultado Financeiro", -40),
                "3.11": ("Lucro/Prejuízo Consolidado do Período", 60),
            }
        ),
    )
    _write_csv(
        b / "financials" / "balance_sheet.csv",
        _statement_rows(
            accounts={
                "1": ("Ativo Total", 2000),
                "1.01": ("Ativo Circulante", 600),
                "1.01.01": ("Caixa e Equivalentes de Caixa", 100),
                "1.01.02": ("Aplicações Financeiras", 50),
                "2": ("Passivo Total", 2000),
                "2.01": ("Passivo Circulante", 500),
                "2.03": ("Patrimônio Líquido Consolidado", 800),
                "2.01.04": ("Empréstimos e Financiamentos", 200),
                "2.02.01": ("Empréstimos e Financiamentos", 300),
            }
        ),
    )
    _write_csv(
        b / "financials" / "cash_flow.csv",
        _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 80)}),
    )

    # CCC3: high leverage + risk notice
    c = _company_tree(tmp_path, "CCC3", "Energia Elétrica")
    _write_csv(
        c / "financials" / "income_statement.csv",
        _statement_rows(
            accounts={
                "3.01": ("Receita de Venda", 1000),
                "3.05": ("Resultado Antes do Resultado Financeiro", 80),
                "3.06": ("Resultado Financeiro", -70),
                "3.11": ("Lucro/Prejuízo Consolidado do Período", 10),
            }
        ),
    )
    _write_csv(
        c / "financials" / "balance_sheet.csv",
        _statement_rows(
            accounts={
                "1": ("Ativo Total", 2000),
                "1.01": ("Ativo Circulante", 300),
                "1.01.01": ("Caixa e Equivalentes de Caixa", 20),
                "1.01.02": ("Aplicações Financeiras", 10),
                "2": ("Passivo Total", 2000),
                "2.01": ("Passivo Circulante", 700),
                "2.03": ("Patrimônio Líquido Consolidado", 400),
                "2.01.04": ("Empréstimos e Financiamentos", 400),
                "2.02.01": ("Empréstimos e Financiamentos", 800),
            }
        ),
    )
    _write_csv(
        c / "financials" / "cash_flow.csv",
        _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 20)}),
    )
    _write_csv(
        c / "notices" / "index.csv",
        [
            {
                "date": "2025-06-01",
                "category": "Fato Relevante",
                "title": "Aviso sobre renegociação de dívida e covenant",
                "source": "IPE",
                "source_url": "",
                "local_path": "",
            }
        ],
    )
    return tmp_path


def test_industry_group_mapping():
    assert industry_group("Energia Elétrica") == "Energy"
    assert industry_group("Bancos") == "Banks"
    assert industry_group("Exploração. Refino e Distribuição") == "Oil & Gas"
    assert industry_group("Unknown Sector XYZ") == "Other"


def test_sector_normalization_expanded():
    """IMP-007: new mappings should not fall through to Other."""
    assert industry_group("Gás") == "Energy"
    assert industry_group("Construção Civil") == "Real Estate"
    assert industry_group("Securitizadoras de Recebíveis") == "Financial Services"
    assert industry_group("Previdência e Seguros") == "Insurance"
    assert industry_group("Transporte Aéreo") == "Transport & Infra"
    assert industry_group("Logística") == "Transport & Infra"
    assert industry_group("Açúcar e Álcool") == "Agribusiness"
    assert industry_group("Máquinas e Equipamentos") == "Industrials"
    assert industry_group("Shoppings Centers") == "Real Estate"
    assert industry_group("Comércio e Distribuição") == "Retail & Consumer"
    assert industry_group("Embalagens") == "Pulp & Paper"
    assert industry_group("Mineração") == "Steel & Mining"


def test_filter_latest_dfp_prefers_ultimo():
    df = pd.DataFrame(
        [
            {
                "DT_REFER": "2024-12-31",
                "SOURCE_DOC": "DFP",
                "ORDEM_EXERC": "PENÚLTIMO",
                "CD_CONTA": "3.01",
                "VL_CONTA": "1",
            },
            {
                "DT_REFER": "2024-12-31",
                "SOURCE_DOC": "DFP",
                "ORDEM_EXERC": "ÚLTIMO",
                "CD_CONTA": "3.01",
                "VL_CONTA": "2",
            },
            {
                "DT_REFER": "2023-12-31",
                "SOURCE_DOC": "DFP",
                "ORDEM_EXERC": "ÚLTIMO",
                "CD_CONTA": "3.01",
                "VL_CONTA": "9",
            },
        ]
    )
    out = _filter_latest_dfp(df)
    assert len(out) == 1
    assert out.iloc[0]["VL_CONTA"] == "2"


def test_pick_account_and_ratios(credit_data: Path):
    kpis = extract_kpis("AAA3")
    assert kpis["has_financials"]
    assert kpis["revenue"] == 1000
    assert kpis["gross_debt"] == 100
    assert kpis["debt_to_equity"] == pytest.approx(0.1)
    assert kpis["current_ratio"] == pytest.approx(2.0)
    assert kpis["interest_coverage"] == pytest.approx(10.0)
    assert kpis["net_margin"] == pytest.approx(0.1)


def test_interest_coverage_positive_fin_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """IMP-004 regression: when 3.06 (financial_result) is positive but 3.06.02
    (interest_expense / despesas financeiras) is negative, interest coverage
    should still be computed from the sub-account."""
    monkeypatch.setattr("decifra.store.folders.COMPANIES_DIR", tmp_path)
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.metrics.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )
    d = _company_tree(tmp_path, "PETR4", "Exploração. Refino e Distribuição")
    # Income: EBIT=200, financial_result=+50 (net positive), interest_expense=-80
    _write_csv(
        d / "financials" / "income_statement.csv",
        _statement_rows(
            accounts={
                "3.01": ("Receita de Venda", 5000),
                "3.05": ("Resultado Antes do Resultado Financeiro", 200),
                "3.06": ("Resultado Financeiro", 50),       # positive net
                "3.06.02": ("Despesas Financeiras", -80),   # negative sub-account
                "3.11": ("Lucro/Prejuízo Consolidado do Período", 170),
            }
        ),
    )
    _write_csv(
        d / "financials" / "balance_sheet.csv",
        _statement_rows(
            accounts={
                "1": ("Ativo Total", 10000),
                "1.01": ("Ativo Circulante", 3000),
                "1.01.01": ("Caixa e Equivalentes de Caixa", 500),
                "1.01.02": ("Aplicações Financeiras", 200),
                "2": ("Passivo Total", 10000),
                "2.01": ("Passivo Circulante", 2000),
                "2.03": ("Patrimônio Líquido Consolidado", 4000),
                "2.01.04": ("Empréstimos e Financiamentos", 1000),
                "2.02.01": ("Empréstimos e Financiamentos", 2000),
            }
        ),
    )
    _write_csv(
        d / "financials" / "cash_flow.csv",
        _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 300)}),
    )
    kpis = extract_kpis("PETR4")
    # Must NOT be None — computed from 3.06.02
    assert kpis["interest_coverage"] is not None
    assert kpis["interest_coverage"] == pytest.approx(200 / 80)


def test_interest_coverage_negative_fin_result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Legacy path: when no 3.06.02 exists but 3.06 is negative, use abs(3.06)."""
    monkeypatch.setattr("decifra.store.folders.COMPANIES_DIR", tmp_path)
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.metrics.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )
    d = _company_tree(tmp_path, "XXX3", "Energia Elétrica")
    _write_csv(
        d / "financials" / "income_statement.csv",
        _statement_rows(
            accounts={
                "3.01": ("Receita de Venda", 1000),
                "3.05": ("Resultado Antes do Resultado Financeiro", 200),
                "3.06": ("Resultado Financeiro", -40),
                "3.11": ("Lucro/Prejuízo Consolidado do Período", 100),
            }
        ),
    )
    _write_csv(d / "financials" / "balance_sheet.csv", _statement_rows(accounts={
        "1": ("Ativo Total", 2000), "2.03": ("Patrimônio Líquido Consolidado", 1000),
    }))
    # No cash_flow.csv — _load_statement will return empty DataFrame
    kpis = extract_kpis("XXX3")
    assert kpis["interest_coverage"] == pytest.approx(200 / 40)


def test_percentile_rank_direction():
    s = pd.Series([1.0, 2.0, 3.0])
    higher = _percentile_rank(s, True)
    lower = _percentile_rank(s, False)
    assert higher.iloc[2] > higher.iloc[0]
    assert lower.iloc[0] > lower.iloc[2]


def test_qualitative_signals(credit_data: Path):
    scan = scan_qualitative_signals("CCC3")
    assert scan["signal_hit_count"] >= 1
    assert scan["qualitative_penalty"] > 0
    assert scan["qualitative_penalty"] <= 15
    assert any("covenant" in k for k in scan["matched_keywords"])


def test_build_credit_table_peer_ranking(credit_data: Path):
    df = build_credit_table(["AAA3", "BBB3", "CCC3"], include_signals=True)
    assert len(df) == 3
    assert set(df["industry_group"]) == {"Energy"}
    aaa = df[df["ticker"] == "AAA3"].iloc[0]
    ccc = df[df["ticker"] == "CCC3"].iloc[0]
    assert aaa["credit_score"] > ccc["credit_score"]
    assert ccc["qualitative_penalty"] > 0
    assert bool(aaa["peer_benchmark"]) is True
