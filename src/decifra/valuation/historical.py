"""Multi-year annual (DFP-only) financial history per ticker.

Credit scoring (`decifra.credit.metrics`) only needs the latest filed period.
Valuation needs a multi-year time series to derive growth, margin, capex,
D&A and working-capital defaults, so this module rebuilds the same
account-code extraction but pivoted across every annual (DFP) `DT_REFER`
found in the local CSVs.

CVM's DFP chart of accounts (`CD_CONTA`) is standardized across companies
("Formulário de Demonstrações Financeiras **Padronizadas**"), so exact code
match is the primary strategy; description-substring fallback is a safety
net for the handful of filings that deviate.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.store.folders import company_dir

INCOME_ACCOUNT_CODES: dict[str, list[str]] = {
    "revenue": ["3.01"],
    "ebit": ["3.05"],
    "financial_result": ["3.06"],
    "interest_expense": ["3.06.02"],
    "pretax_income": ["3.07"],
    "tax_expense": ["3.08"],
    "net_income": ["3.11"],
    "net_income_controllers": ["3.11.01"],
}

BALANCE_ACCOUNT_CODES: dict[str, list[str]] = {
    "total_assets": ["1"],
    "current_assets": ["1.01"],
    "cash": ["1.01.01"],
    "st_investments": ["1.01.02"],
    "total_liabilities": ["2"],
    "current_liabilities": ["2.01"],
    "equity": ["2.03"],
    "debt_st": ["2.01.04"],
    "debt_lt": ["2.02.01"],
}

CASHFLOW_ACCOUNT_CODES: dict[str, list[str]] = {
    "operating_cf": ["6.01"],
    "depreciation_amortization": ["6.01.01.04"],
    "nwc_change_cf": ["6.01.02"],
    "capex": ["6.02.01"],
    "investing_cf": ["6.02"],
}

DESC_FALLBACK: dict[str, list[str]] = {
    "revenue": ["receita de venda", "receita liquida", "receitas de intermediacao"],
    "ebit": ["antes do resultado financeiro"],
    "financial_result": ["resultado financeiro"],
    "interest_expense": ["despesas financeiras"],
    "pretax_income": ["antes dos tributos sobre o lucro"],
    "tax_expense": ["imposto de renda e contribuicao social sobre o lucro"],
    "net_income": ["lucro/prejuizo consolidado", "lucro liquido"],
    "net_income_controllers": [
        "atribuido a socios da empresa controladora",
        "atribuido aos acionistas controladores",
    ],
    "total_assets": ["ativo total"],
    "current_assets": ["ativo circulante"],
    "cash": ["caixa e equivalentes"],
    "st_investments": ["aplicacoes financeiras"],
    "total_liabilities": ["passivo total"],
    "current_liabilities": ["passivo circulante"],
    "equity": ["patrimonio liquido"],
    "debt_st": ["emprestimos e financiamentos"],
    "debt_lt": ["emprestimos e financiamentos"],
    "operating_cf": [
        "caixa liquido atividades operacionais",
        "caixa liquido gerado atividades operacionais",
    ],
    "depreciation_amortization": [
        "depreciacao, deplecao e amortizacao",
        "depreciacao e amortizacao",
    ],
    "nwc_change_cf": ["variacoes nos ativos e passivos"],
    "capex": [
        "aquisicoes de ativos imobilizados e intangiveis",
        "aquisicao de ativo imobilizado",
    ],
    "investing_cf": ["caixa liquido atividades de investimento"],
}

ALL_ACCOUNT_CODES: dict[str, list[str]] = {
    **INCOME_ACCOUNT_CODES,
    **BALANCE_ACCOUNT_CODES,
    **CASHFLOW_ACCOUNT_CODES,
}

# Columns kept as absolute R$ (thousands, per CVM convention) in the history frame
_VALUE_COLUMNS: list[str] = list(ALL_ACCOUNT_CODES) + ["gross_debt", "net_debt"]


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm(text: str) -> str:
    return _strip_accents(str(text or "")).lower().strip()


def _is_ultimo(ordem: str) -> bool:
    n = _norm(ordem)
    return "ltimo" in n and "pen" not in n


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip().replace(",", ".")
    if not s or s.lower() in {"nan", "none", ""}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _load_statement(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, dtype=str).fillna("")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _dfp_only(df: pd.DataFrame) -> pd.DataFrame:
    """Keep annual (DFP) filings with the ÚLTIMO exercise order (final restated figure)."""
    if df.empty:
        return df
    work = df.copy()
    if "SOURCE_DOC" in work.columns:
        dfp = work[work["SOURCE_DOC"].str.upper() == "DFP"]
        if not dfp.empty:
            work = dfp
    if "ORDEM_EXERC" in work.columns:
        ultimo = work[work["ORDEM_EXERC"].map(_is_ultimo)]
        if not ultimo.empty:
            work = ultimo
    return work


def _scale_factor(period_df: pd.DataFrame) -> float:
    """CVM reports monetary accounts in thousands (`ESCALA_MOEDA=MIL`) by convention.

    Valuation combines these figures with market data (price x shares, in
    absolute R$), so every monetary value read here is normalized to
    absolute reais — unlike `credit/metrics.py`, which only ever computes
    scale-invariant ratios and can safely leave figures in "thousands".
    """
    if period_df.empty or "ESCALA_MOEDA" not in period_df.columns:
        return 1.0
    escala = _norm(str(period_df["ESCALA_MOEDA"].iloc[0]))
    if "milh" in escala:  # "MILHÃO" / "MILHOES"
        return 1_000_000.0
    if "mil" in escala:  # "MIL"
        return 1_000.0
    return 1.0


def _pick_for_period(period_df: pd.DataFrame, kpi: str, codes: list[str]) -> float | None:
    if period_df.empty or "CD_CONTA" not in period_df.columns:
        return None
    scale = _scale_factor(period_df)
    for code in codes:
        exact = period_df[period_df["CD_CONTA"] == code]
        if not exact.empty:
            v = _to_float(exact.iloc[0]["VL_CONTA"])
            return v * scale if v is not None else None
    needles = DESC_FALLBACK.get(kpi, [])
    if not needles or "DS_CONTA" not in period_df.columns:
        return None
    desc_norm = period_df["DS_CONTA"].map(_norm)
    for needle in needles:
        n = _norm(needle)
        hits = period_df[desc_norm.str.contains(n, na=False)]
        if hits.empty:
            continue
        hits = hits.copy()
        hits["_depth"] = hits["CD_CONTA"].str.count(r"\.")
        hits = hits.sort_values("_depth")
        if kpi in {"debt_st", "debt_lt"}:
            for code in codes:
                exact = hits[hits["CD_CONTA"] == code]
                if not exact.empty:
                    v = _to_float(exact.iloc[0]["VL_CONTA"])
                    return v * scale if v is not None else None
            continue
        v = _to_float(hits.iloc[0]["VL_CONTA"])
        return v * scale if v is not None else None
    return None


def _series_for_kpi(df: pd.DataFrame, kpi: str, codes: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    if df.empty or "DT_REFER" not in df.columns:
        return out
    for period, period_df in df.groupby("DT_REFER"):
        val = _pick_for_period(period_df, kpi, codes)
        if val is not None:
            out[str(period)] = val
    return out


def build_annual_history(ticker: str, *, max_years: int = 6) -> pd.DataFrame:
    """One row per fiscal year end (most recent `max_years`), DFP-only.

    Columns: `period` plus every key in `ALL_ACCOUNT_CODES`, `gross_debt`,
    `net_debt`, and derived per-year ratios (`ebit_margin`,
    `effective_tax_rate`, `revenue_growth`, `da_pct_revenue`,
    `capex_pct_revenue`, `nwc_pct_revenue`).
    """
    root = company_dir(ticker) / "financials"
    income = _dfp_only(_load_statement(root / "income_statement.csv"))
    balance = _dfp_only(_load_statement(root / "balance_sheet.csv"))
    cashflow = _dfp_only(_load_statement(root / "cash_flow.csv"))

    series: dict[str, dict[str, float]] = {}
    for kpi, codes in INCOME_ACCOUNT_CODES.items():
        series[kpi] = _series_for_kpi(income, kpi, codes)
    for kpi, codes in BALANCE_ACCOUNT_CODES.items():
        series[kpi] = _series_for_kpi(balance, kpi, codes)
    for kpi, codes in CASHFLOW_ACCOUNT_CODES.items():
        series[kpi] = _series_for_kpi(cashflow, kpi, codes)

    periods: set[str] = set()
    for s in series.values():
        periods.update(s.keys())
    if not periods:
        return pd.DataFrame(columns=["period", *_VALUE_COLUMNS])

    rows: list[dict[str, Any]] = []
    for p in sorted(periods):
        row: dict[str, Any] = {"period": p}
        for kpi, s in series.items():
            row[kpi] = s.get(p)
        debt_st = row.get("debt_st")
        debt_lt = row.get("debt_lt")
        cash = row.get("cash") or 0.0
        st_inv = row.get("st_investments") or 0.0
        if debt_st is not None or debt_lt is not None:
            gross_debt = (debt_st or 0.0) + (debt_lt or 0.0)
            row["gross_debt"] = gross_debt
            row["net_debt"] = gross_debt - cash - st_inv
        else:
            row["gross_debt"] = None
            row["net_debt"] = None
        rows.append(row)

    hist = pd.DataFrame(rows).sort_values("period").tail(max_years).reset_index(drop=True)
    numeric_cols = [c for c in hist.columns if c != "period"]
    hist[numeric_cols] = hist[numeric_cols].apply(pd.to_numeric, errors="coerce")

    def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
        b_safe = b.mask(b == 0)
        return a / b_safe

    revenue = hist["revenue"]
    hist["ebit_margin"] = _safe_div(hist["ebit"], revenue)
    hist["effective_tax_rate"] = _safe_div(-hist["tax_expense"], hist["pretax_income"].mask(hist["pretax_income"] <= 0))
    hist["revenue_growth"] = revenue.pct_change()
    hist["da_pct_revenue"] = _safe_div(hist["depreciation_amortization"], revenue)
    # capex / NWC are stored with their natural CF-statement sign (outflow = negative);
    # the *_pct_revenue ratios below are positive "intensity" figures for reporting/UI.
    hist["capex_pct_revenue"] = _safe_div(-hist["capex"], revenue)
    hist["nwc_pct_revenue"] = _safe_div(-hist["nwc_change_cf"], revenue)
    return hist


def cagr(hist: pd.DataFrame, field: str, years: int) -> float | None:
    """Compound annual growth rate of `field` over the trailing `years` (uses available data if fewer)."""
    if hist.empty or field not in hist.columns:
        return None
    series = hist[field].dropna()
    if len(series) < 2:
        return None
    window = series.tail(years + 1)
    if len(window) < 2:
        return None
    start, end = window.iloc[0], window.iloc[-1]
    n = len(window) - 1
    if start is None or end is None or start <= 0 or end <= 0 or n <= 0:
        return None
    return (end / start) ** (1.0 / n) - 1.0


def trailing_average(hist: pd.DataFrame, field: str, years: int) -> float | None:
    """Simple average of the trailing `years` of a ratio column, ignoring NaNs."""
    if hist.empty or field not in hist.columns:
        return None
    window = hist[field].dropna().tail(years)
    if window.empty:
        return None
    return float(window.mean())


def trailing_median(hist: pd.DataFrame, field: str, years: int) -> float | None:
    """Median of the trailing `years` of a column, ignoring NaNs — robust to one-off cycles."""
    if hist.empty or field not in hist.columns:
        return None
    window = hist[field].dropna().tail(years)
    if window.empty:
        return None
    return float(window.median())
