from __future__ import annotations

import pandas as pd

from decifra.assistant.retrieve import extract_ticker, extract_year
from decifra.cvm.financials import _normalize_statement


def test_normalize_statement_adds_cnpj():
    df = pd.DataFrame(
        {
            "CNPJ_CIA": ["33.000.167/0001-01"],
            "DENOM_CIA": ["PETROLEO BRASILEIRO S.A."],
            "CD_CONTA": ["3.01"],
            "DS_CONTA": ["Receita de Venda de Bens e/ou Serviços"],
            "VL_CONTA": ["1000"],
        }
    )
    out = _normalize_statement(df, "DFP", 2024)
    assert out.iloc[0]["CNPJ_NORM"] == "33000167000101"
    assert out.iloc[0]["SOURCE_DOC"] == "DFP"


def test_extract_ticker_and_year():
    assert extract_year("receita da vale em 2024") == "2024"
    # Without universe file, regex still works
    assert extract_ticker("Mostre PETR4 lucro líquido") == "PETR4"
