from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.store.folders import company_dir, load_meta


# Account codes → logical KPI names (exact CD_CONTA match preferred)
ACCOUNT_CODES: dict[str, list[str]] = {
    "revenue": ["3.01"],
    "ebit": ["3.05"],
    "financial_result": ["3.06"],
    "interest_expense": ["3.06.02"],
    "net_income": ["3.11"],
    "total_assets": ["1"],
    "current_assets": ["1.01"],
    "cash": ["1.01.01"],
    "st_investments": ["1.01.02"],
    "total_liabilities": ["2"],
    "current_liabilities": ["2.01"],
    "equity": ["2.03"],
    "debt_st": ["2.01.04"],
    "debt_lt": ["2.02.01"],
    "operating_cf": ["6.01"],
}

# Description substrings used when code is missing
ACCOUNT_DESC_FALLBACK: dict[str, list[str]] = {
    "revenue": ["receita de venda", "receita líquida", "receitas de intermediação"],
    "ebit": ["antes do resultado financeiro"],
    "financial_result": ["resultado financeiro"],
    "interest_expense": ["despesas financeiras", "juros sobre empréstimos", "juros e variações"],
    "net_income": ["lucro/prejuízo consolidado", "lucro líquido"],
    "total_assets": ["ativo total"],
    "current_assets": ["ativo circulante"],
    "cash": ["caixa e equivalentes"],
    "st_investments": ["aplicações financeiras"],
    "total_liabilities": ["passivo total"],
    "current_liabilities": ["passivo circulante"],
    "equity": ["patrimônio líquido"],
    "debt_st": ["empréstimos e financiamentos"],
    "debt_lt": ["empréstimos e financiamentos"],
    "operating_cf": ["caixa líquido atividades operacionais", "caixa liquido atividades operacionais"],
}


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
    df = pd.read_csv(path, dtype=str).fillna("")
    return df


def _filter_latest_dfp(df: pd.DataFrame) -> pd.DataFrame:
    """Prefer latest annual DFP period and ÚLTIMO exercise order."""
    if df.empty:
        return df
    work = df.copy()
    if "SOURCE_DOC" in work.columns:
        dfp = work[work["SOURCE_DOC"].str.upper() == "DFP"]
        if not dfp.empty:
            work = dfp
    if "DT_REFER" not in work.columns:
        return work
    latest = work["DT_REFER"].max()
    work = work[work["DT_REFER"] == latest]
    if "ORDEM_EXERC" in work.columns:
        ultimo = work[work["ORDEM_EXERC"].map(_is_ultimo)]
        if not ultimo.empty:
            work = ultimo
    return work


def _pick_account(df: pd.DataFrame, kpi: str) -> float | None:
    if df.empty or "CD_CONTA" not in df.columns:
        return None
    codes = ACCOUNT_CODES.get(kpi, [])
    for code in codes:
        exact = df[df["CD_CONTA"] == code]
        if not exact.empty:
            return _to_float(exact.iloc[0]["VL_CONTA"])
    # Description fallback (exact parent rows tend to be shorter codes)
    needles = ACCOUNT_DESC_FALLBACK.get(kpi, [])
    if not needles or "DS_CONTA" not in df.columns:
        return None
    desc_norm = df["DS_CONTA"].map(_norm)
    for needle in needles:
        n = _norm(needle)
        mask = desc_norm.str.contains(n, na=False)
        hits = df[mask]
        if hits.empty:
            continue
        # Prefer shallowest account code
        hits = hits.copy()
        hits["_depth"] = hits["CD_CONTA"].str.count(r"\.")
        hits = hits.sort_values("_depth")
        # For debt accounts, only match top-level empréstimos codes
        if kpi in {"debt_st", "debt_lt"}:
            for code in codes:
                exact = hits[hits["CD_CONTA"] == code]
                if not exact.empty:
                    return _to_float(exact.iloc[0]["VL_CONTA"])
            continue
        return _to_float(hits.iloc[0]["VL_CONTA"])
    return None


def extract_kpis(ticker: str) -> dict[str, Any]:
    """Extract latest DFP KPIs and credit ratios for one ticker."""
    root = company_dir(ticker) / "financials"
    meta = load_meta(ticker)
    income = _filter_latest_dfp(_load_statement(root / "income_statement.csv"))
    balance = _filter_latest_dfp(_load_statement(root / "balance_sheet.csv"))
    cashflow = _filter_latest_dfp(_load_statement(root / "cash_flow.csv"))

    period = ""
    for frame in (income, balance, cashflow):
        if not frame.empty and "DT_REFER" in frame.columns:
            period = str(frame["DT_REFER"].iloc[0])
            break

    kpis: dict[str, Any] = {
        "ticker": ticker.upper(),
        "company": meta.get("company_name") or meta.get("stock_name") or ticker,
        "sector": meta.get("sector") or "",
        "period": period,
        "has_financials": not (income.empty and balance.empty),
    }

    for kpi in ACCOUNT_CODES:
        source = cashflow if kpi == "operating_cf" else income if kpi in {
            "revenue",
            "ebit",
            "financial_result",
            "interest_expense",
            "net_income",
        } else balance
        kpis[kpi] = _pick_account(source, kpi)

    revenue = kpis.get("revenue")
    ebit = kpis.get("ebit")
    fin_res = kpis.get("financial_result")
    net_income = kpis.get("net_income")
    assets = kpis.get("total_assets")
    current_assets = kpis.get("current_assets")
    cash = kpis.get("cash") or 0.0
    st_inv = kpis.get("st_investments") or 0.0
    current_liab = kpis.get("current_liabilities")
    equity = kpis.get("equity")
    debt_st = kpis.get("debt_st") or 0.0
    debt_lt = kpis.get("debt_lt") or 0.0
    op_cf = kpis.get("operating_cf")

    gross_debt = (debt_st or 0.0) + (debt_lt or 0.0)
    liquid_assets = (cash or 0.0) + (st_inv or 0.0)
    net_debt = gross_debt - liquid_assets

    kpis["gross_debt"] = gross_debt if (kpis.get("debt_st") is not None or kpis.get("debt_lt") is not None) else None
    kpis["net_debt"] = net_debt if kpis["gross_debt"] is not None else None
    kpis["liquid_assets"] = liquid_assets

    # Ratios (NaN-safe via None)
    def _div(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or b == 0:
            return None
        return a / b

    kpis["debt_to_equity"] = _div(kpis["gross_debt"], equity)
    kpis["net_debt_to_cash"] = _div(kpis["net_debt"], liquid_assets if liquid_assets else None)
    kpis["current_ratio"] = _div(current_assets, current_liab)
    # Interest coverage: prefer sub-account 3.06.02 (despesas financeiras),
    # fall back to parent 3.06 (resultado financeiro) when negative.
    # Fixes IMP-004: PETR4 has positive 3.06 (net revenues > expenses)
    # but negative 3.06.02 (the expense portion).
    int_exp = kpis.get("interest_expense")
    if int_exp is not None and int_exp < 0 and ebit is not None:
        kpis["interest_coverage"] = _div(ebit, abs(int_exp))
    elif ebit is not None and fin_res is not None and fin_res < 0:
        kpis["interest_coverage"] = _div(ebit, abs(fin_res))
    else:
        kpis["interest_coverage"] = None
    kpis["ocf_to_net_debt"] = _div(op_cf, net_debt if net_debt and net_debt > 0 else None)
    kpis["net_margin"] = _div(net_income, revenue)
    kpis["ebit_margin"] = _div(ebit, revenue)
    kpis["equity_to_assets"] = _div(equity, assets)
    kpis["roe"] = _div(net_income, equity)

    return kpis


def extract_kpis_frame(tickers: list[str]) -> pd.DataFrame:
    rows = [extract_kpis(t) for t in tickers]
    return pd.DataFrame(rows)
