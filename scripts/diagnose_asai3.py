#!/usr/bin/env python3
r"""Diagnose why ASAI3 has no income/balance/cash CSVs.

Checks:
1. ASAI3 meta.json — is CNPJ mapped?
2. CVM cadastro — search for ASSAI / SENDAS
3. CVM DFP/ITR ZIPs — does data exist for the CNPJ?
4. Document findings

Usage:
    .\.venv\Scripts\python.exe scripts\diagnose_asai3.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from decifra.config import CADASTRO_CSV, CVM_CACHE_DIR, CVM_DFP_ZIP
from decifra.cvm.download import ensure_zip, read_csv_from_zip
from decifra.http_util import normalize_cnpj
from decifra.store.folders import company_dir, load_meta

TICKER = "ASAI3"


def main() -> int:
    print(f"=== Diagnosing {TICKER} financial data absence ===\n")

    # 1. Check meta.json
    meta = load_meta(TICKER)
    if not meta:
        print(f"[FAIL] No meta.json found for {TICKER}")
        print(f"       Expected: {company_dir(TICKER) / 'meta.json'}")
        print("       → Run 'decifra sync universe' first.")
        return 1

    cnpj = meta.get("cnpj", "")
    company_name = meta.get("company_name") or meta.get("stock_name") or ""
    cvm_code = meta.get("cvm_code", "")
    print(f"meta.json:")
    print(f"  ticker:       {meta.get('ticker')}")
    print(f"  company_name: {company_name}")
    print(f"  cnpj:         {cnpj or '(empty!)'}")
    print(f"  cvm_code:     {cvm_code or '(empty)'}")
    print(f"  sector:       {meta.get('sector', '')}")

    # 2. Check existing financial CSVs
    root = company_dir(TICKER) / "financials"
    for name in ("income_statement.csv", "balance_sheet.csv", "cash_flow.csv", "prices.csv"):
        path = root / name
        if path.exists() and path.stat().st_size > 50:
            print(f"  {name}: EXISTS ({path.stat().st_size:,} bytes)")
        else:
            print(f"  {name}: MISSING")

    # 3. Search CVM cadastro
    print(f"\n--- CVM cadastro search ---")
    if CADASTRO_CSV.exists():
        import pandas as pd
        cad = pd.read_csv(CADASTRO_CSV, dtype=str, sep=";", encoding="latin-1")
        # Search for ASSAI or SENDAS (historical name)
        for needle in ("ASSAI", "SENDAS", "ASAI"):
            hits = cad[cad["DENOM_SOCIAL"].fillna("").str.upper().str.contains(needle)]
            if not hits.empty:
                print(f"  Found '{needle}':")
                for _, row in hits.head(5).iterrows():
                    cnpj_found = normalize_cnpj(row.get("CNPJ_CIA", ""))
                    print(f"    DENOM_SOCIAL: {row.get('DENOM_SOCIAL')}")
                    print(f"    CNPJ_CIA:     {row.get('CNPJ_CIA')} -> normalized: {cnpj_found}")
                    print(f"    CD_CVM:       {row.get('CD_CVM')}")
                    print(f"    SIT_REG:      {row.get('SIT_REG')}")
            else:
                print(f"  No match for '{needle}'")
    else:
        print(f"  cadastro CSV not found at {CADASTRO_CSV}")
        print("  → Run 'decifra sync universe --force-cadastro'")

    # 4. Search DFP ZIPs for the CNPJ
    print(f"\n--- CVM DFP data search ---")
    if cnpj:
        norm_cnpj = normalize_cnpj(cnpj)
        print(f"  Searching for CNPJ {norm_cnpj} in DFP ZIPs...")
        for year in range(2020, 2027):
            zip_url = CVM_DFP_ZIP.format(year=year)
            zip_path = CVM_CACHE_DIR / f"dfp_cia_aberta_{year}.zip"
            if not zip_path.exists():
                print(f"  {year}: ZIP not cached (skip)")
                continue
            try:
                df = read_csv_from_zip(zip_path, "DRE_con")
                if "CNPJ_CIA" in df.columns:
                    df["CNPJ_NORM"] = df["CNPJ_CIA"].map(normalize_cnpj)
                    hits = df[df["CNPJ_NORM"] == norm_cnpj]
                    if not hits.empty:
                        print(f"  {year}: FOUND {len(hits)} DRE rows for {norm_cnpj}")
                    else:
                        print(f"  {year}: no DRE rows for {norm_cnpj}")
            except Exception as e:
                print(f"  {year}: error reading ZIP: {e}")
    else:
        print("  No CNPJ in meta.json — cannot search DFP data.")
        print("  This is the root cause: CNPJ mapping failed during sync.")
        print("  ASAI3 (Assaí Atacadista) was spun off from GPA in 2021.")
        print("  The company trades under a different legal entity name at CVM:")
        print("    'SENDAS DISTRIBUIDORA S.A.' (CNPJ: 47.508.411/0001-56)")

    # 5. Diagnosis summary
    print(f"\n=== DIAGNOSIS ===")
    if not cnpj:
        print(f"ROOT CAUSE: {TICKER} has no CNPJ mapping in meta.json.")
        print("ASAI3 (Assaí Atacadista) is listed at CVM as 'SENDAS DISTRIBUIDORA S.A.'")
        print("The B3 ticker name 'ASSAI' doesn't match 'SENDAS' in the CVM cadastro,")
        print("so the fuzzy CNPJ matching in sync_financials fails.")
        print()
        print("FIX OPTIONS:")
        print("  1. Manually set cnpj in meta.json to 47508411000156 (if that's the correct CNPJ)")
        print("  2. Add a ticker→CNPJ override table in the sync pipeline")
        print()
        print("This should be documented as a known CVM dump gap in improvements LOG.")
    else:
        print(f"CNPJ is set ({cnpj}), but financial CSVs are missing.")
        print("Check if the CNPJ matches the company in CVM DFP ZIPs.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
