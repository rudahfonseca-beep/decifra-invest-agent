from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decifra.credit.scoring import build_credit_table
from decifra.report.assemble import assemble_context
from decifra.report.spec import EntitySelection, ReportSpec, validate_spec


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
    return rows


@pytest.fixture
def report_credit_df(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> pd.DataFrame:
    monkeypatch.setattr("decifra.store.folders.COMPANIES_DIR", tmp_path)
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.signals.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.scoring.list_tickers",
        lambda t=None: ["AAA3", "BBB3", "CCC3"] if not t else [t.upper()],
    )
    monkeypatch.setattr("decifra.credit.scoring.load_universe", lambda: {"constituents": []})
    monkeypatch.setattr(
        "decifra.credit.metrics.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        "decifra.credit.scoring.load_identity",
        lambda t: json.loads((tmp_path / t.upper() / "meta.json").read_text(encoding="utf-8")),
    )

    for ticker, debt_st, debt_lt, ni in (
        ("AAA3", 50, 50, 100),
        ("BBB3", 200, 300, 60),
        ("CCC3", 400, 600, 20),
    ):
        root = _company_tree(tmp_path, ticker)
        _write_csv(
            root / "financials" / "income_statement.csv",
            _statement_rows(
                accounts={
                    "3.01": ("Receita de Venda", 1000),
                    "3.05": ("Resultado Antes do Resultado Financeiro", 200),
                    "3.06": ("Resultado Financeiro", -20),
                    "3.11": ("Lucro/Prejuízo Consolidado do Período", ni),
                }
            ),
        )
        _write_csv(
            root / "financials" / "balance_sheet.csv",
            _statement_rows(
                accounts={
                    "1": ("Ativo Total", 2000),
                    "1.01": ("Ativo Circulante", 800),
                    "1.01.01": ("Caixa e Equivalentes de Caixa", 300),
                    "1.01.02": ("Aplicações Financeiras", 100),
                    "2": ("Passivo Total", 2000),
                    "2.01": ("Passivo Circulante", 400),
                    "2.03": ("Patrimônio Líquido Consolidado", 1000),
                    "2.01.04": ("Empréstimos e Financiamentos", debt_st),
                    "2.02.01": ("Empréstimos e Financiamentos", debt_lt),
                }
            ),
        )
        _write_csv(
            root / "financials" / "cash_flow.csv",
            _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 150)}),
        )

    return build_credit_table(include_signals=False)


def test_assemble_company_only(report_credit_df: pd.DataFrame) -> None:
    spec = validate_spec(
        ReportSpec(
            mode="credit",
            subjects=EntitySelection(companies=["AAA3"]),
            kpis=["debt_to_equity", "credit_score"],
            include_signals=False,
        ),
        known_tickers=["AAA3", "BBB3", "CCC3"],
        known_industries=["Energy"],
    )
    ctx = assemble_context(spec, credit_df=report_credit_df)
    assert ctx["mode"] == "credit"
    assert len(ctx["companies"]) == 1
    assert ctx["companies"][0]["found"] is True
    assert ctx["companies"][0]["role"] == "subject"
    assert "debt_to_equity" in ctx["companies"][0]["kpis"]
    assert ctx["industries"] == []


def test_assemble_industry_only(report_credit_df: pd.DataFrame) -> None:
    spec = validate_spec(
        ReportSpec(
            mode="credit",
            subjects=EntitySelection(industries=["Energy"]),
            include_signals=False,
        ),
        known_tickers=["AAA3", "BBB3", "CCC3"],
        known_industries=["Energy"],
    )
    ctx = assemble_context(spec, credit_df=report_credit_df)
    assert len(ctx["industries"]) == 1
    ind = ctx["industries"][0]
    assert ind["found"] is True
    assert ind["with_financials"] == 3
    assert ind["score_distribution"]["count"] == 3
    assert len(ind["ranked_members"]) == 3


def test_assemble_comparative_equity(report_credit_df: pd.DataFrame) -> None:
    spec = validate_spec(
        ReportSpec(
            mode="equity",
            subjects=EntitySelection(companies=["AAA3"]),
            comparatives=EntitySelection(companies=["CCC3"], industries=["Energy"]),
            kpis=["roe", "ebit_margin", "net_margin"],
            include_signals=False,
        ),
        known_tickers=["AAA3", "BBB3", "CCC3"],
        known_industries=["Energy"],
    )
    ctx = assemble_context(spec, credit_df=report_credit_df)
    roles = [c["role"] for c in ctx["companies"]]
    assert roles == ["subject", "comparative"]
    assert ctx["industries"][0]["role"] == "comparative"
    assert any(c["id"].startswith("compare_") for c in ctx["chart_specs"])
    # ebit_margin should be present on credit table after metrics change
    assert "ebit_margin" in report_credit_df.columns
    assert ctx["companies"][0]["kpis"]["ebit_margin"]["value"] is not None
