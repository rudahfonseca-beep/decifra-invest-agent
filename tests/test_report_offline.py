"""Tests for the offline HTML report renderer (IMP-012)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from decifra.credit.scoring import build_credit_table
from decifra.report.assemble import assemble_context
from decifra.report.generate import build_report_artifacts
from decifra.report.render_offline import render_offline_html
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
def offline_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr("decifra.store.folders.COMPANIES_DIR", tmp_path)
    monkeypatch.setattr("decifra.credit.metrics.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr("decifra.credit.signals.company_dir", lambda t: tmp_path / t.upper())
    monkeypatch.setattr(
        "decifra.credit.scoring.list_tickers",
        lambda t=None: ["AAA3", "BBB3"] if not t else [t.upper()],
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

    for ticker in ("AAA3", "BBB3"):
        root = _company_tree(tmp_path, ticker)
        _write_csv(
            root / "financials" / "income_statement.csv",
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
                    "2.01.04": ("Empréstimos e Financiamentos", 50),
                    "2.02.01": ("Empréstimos e Financiamentos", 50),
                }
            ),
        )
        _write_csv(
            root / "financials" / "cash_flow.csv",
            _statement_rows(accounts={"6.01": ("Caixa Líquido Atividades Operacionais", 150)}),
        )

    credit_df = build_credit_table(include_signals=False)
    spec = validate_spec(
        ReportSpec(
            mode="credit",
            subjects=EntitySelection(companies=["AAA3"], industries=["Energy"]),
            include_signals=False,
        ),
        known_tickers=["AAA3", "BBB3"],
        known_industries=["Energy"],
    )
    return assemble_context(spec, credit_df=credit_df)


def test_render_offline_produces_valid_html(offline_context: dict) -> None:
    html = render_offline_html(offline_context)
    assert "<!DOCTYPE html>" in html
    assert "Plotly.newPlot" in html
    assert "AAA3" in html
    assert "Energy" in html
    assert offline_context["disclaimer"] in html


def test_render_offline_has_kpi_values(offline_context: dict) -> None:
    html = render_offline_html(offline_context)
    # Should contain formatted percentage KPIs
    assert "%" in html  # net_margin, roe etc.
    assert "Debt / Equity" in html or "debt_to_equity" in html


def test_build_report_artifacts_offline(
    tmp_path: Path, offline_context: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_report_artifacts with offline=True should produce report.html."""
    spec = ReportSpec(
        mode="credit",
        subjects=EntitySelection(companies=["AAA3"], industries=["Energy"]),
        include_signals=False,
    )
    # Monkey-patch assemble_context to return our fixture
    monkeypatch.setattr(
        "decifra.report.generate.assemble_context",
        lambda s, credit_df=None: offline_context,
    )
    result = build_report_artifacts(spec, offline=True, out_dir=tmp_path)
    assert result["ok"]
    assert result["generated"]
    assert result["html_path"] is not None
    html_path = Path(result["html_path"])
    assert html_path.exists()
    html = html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
