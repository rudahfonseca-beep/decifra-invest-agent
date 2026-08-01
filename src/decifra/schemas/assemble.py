"""Assemble the three standardized pipeline output tables."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from decifra.credit.capacity import evaluate_capacity
from decifra.store.folders import company_dir, load_identity
from decifra.valuation.waterfall import ocf_to_fcfe_waterfall


def _metric(value: Any, source_doc: str, **extra: Any) -> dict[str, Any]:
    return {
        "value": value,
        "lineage": {"source_doc": source_doc, **extra},
    }


def assemble_company_profile(ticker: str) -> dict[str, Any]:
    ident = load_identity(ticker)
    return {
        "ticker": ticker.upper(),
        "cnpj": ident.get("cnpj") or "",
        "cvm_code": str(ident.get("cvm_code") or ""),
        "company_name": ident.get("company_name") or "",
        "isins": ident.get("isins") or [],
        "currency": "BRL",
        "metrics": {
            "identity_source": _metric(
                ",".join(ident.get("entity_sources") or ["meta.json"]),
                "entities.json|meta.json",
            )
        },
    }


def assemble_credit_debt_matrix(
    ticker: str,
    *,
    net_debt: float | None = None,
    ebitda: float | None = None,
    ocf: float | None = None,
    debt_service: float | None = None,
) -> dict[str, Any]:
    root = company_dir(ticker)
    facilities: list[dict[str, Any]] = []
    for name, source in (
        ("anbima_instruments.csv", "ANBIMA"),
        ("b3_balcao_bonds.csv", "B3_BALCAO"),
    ):
        path = root / "debt" / name
        if not path.exists():
            continue
        df = pd.read_csv(path, dtype=str)
        for _, row in df.iterrows():
            facilities.append(
                {
                    "isin_or_code": row.get("isin") or row.get("code") or "",
                    "instrument_type": row.get("instrument_type") or "",
                    "indexer": row.get("indexer") or "",
                    "yield_pct": float(row["yield_pct"]) if row.get("yield_pct") not in (None, "") else None,
                    "maturity": row.get("maturity") or "",
                    "outstanding_brl": float(row["outstanding_brl"])
                    if row.get("outstanding_brl") not in (None, "")
                    else None,
                    "covenant_text": row.get("covenant_text") or "",
                    "lineage": {"source_doc": source},
                }
            )

    cap = None
    if all(v is not None for v in (net_debt, ebitda, ocf, debt_service)):
        cap = evaluate_capacity(
            net_debt=net_debt,
            ebitda=ebitda,
            ocf_or_ebitda_proxy=ocf,
            debt_service=debt_service,
            lineage={"source_doc": "capacity"},
        ).to_dict()
    else:
        cap = {
            "net_debt_ebitda": None,
            "dscr": None,
            "any_breach": False,
            "lineage": {"source_doc": "capacity"},
        }

    return {
        "ticker": ticker.upper(),
        "as_of": None,
        "facilities": facilities,
        "capacity": {
            "net_debt_ebitda": (cap.get("net_debt_ebitda") or {}).get("value")
            if isinstance(cap.get("net_debt_ebitda"), dict)
            else cap.get("net_debt_ebitda"),
            "dscr": (cap.get("dscr") or {}).get("value")
            if isinstance(cap.get("dscr"), dict)
            else cap.get("dscr"),
            "any_breach": cap.get("any_breach", False),
            "lineage": {"source_doc": "capacity"},
        },
    }


def assemble_valuation_waterfall(
    ticker: str,
    *,
    ocf: float,
    interest: float,
    amortization: float = 0.0,
) -> dict[str, Any]:
    wf = ocf_to_fcfe_waterfall(
        ocf=ocf,
        interest=interest,
        mandatory_amortization=amortization,
        lineage={"source_doc": "waterfall"},
    )
    return {
        "ticker": ticker.upper(),
        "method": "OCF_FCFE",
        "inputs": {
            "ocf": _metric(ocf, "CVM_DFP_ITR"),
            "interest": _metric(interest, "CVM_DFP_ITR"),
            "mandatory_amortization": _metric(amortization, "debt_schedule"),
        },
        "outputs": {
            "ocf": wf.ocf,
            "debt_service": wf.debt_service,
            "fcfe": wf.fcfe,
            "v_u": None,
            "pv_tax_shield": None,
            "v_l": None,
        },
        "lineage": {"source_doc": "valuation_waterfall"},
    }


def write_sample_bundle(out_dir: Path, ticker: str = "PETR4") -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    import json

    profile = assemble_company_profile(ticker)
    matrix = assemble_credit_debt_matrix(ticker, net_debt=700, ebitda=200, ocf=250, debt_service=100)
    waterfall = assemble_valuation_waterfall(ticker, ocf=250, interest=80, amortization=20)
    paths = {}
    for name, payload in (
        ("company_profile.json", profile),
        ("credit_debt_matrix.json", matrix),
        ("valuation_waterfall.json", waterfall),
    ):
        path = out_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[name] = path
    return paths
