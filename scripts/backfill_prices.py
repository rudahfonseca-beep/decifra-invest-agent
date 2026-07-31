#!/usr/bin/env python3
r"""Backfill prices.csv for all Ibovespa tickers missing OHLCV data.

Uses BRAPI_API_KEY if present in .env, otherwise falls back to yfinance.
Spot-checks PETR4/VALE3/ITUB4 at the end.

Usage:
    .\.venv\Scripts\python.exe scripts/backfill_prices.py
    .\.venv\Scripts\python.exe scripts/backfill_prices.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from decifra.config import BRAPI_API_KEY
from decifra.cvm.financials import sync_prices
from decifra.store.folders import company_dir, list_tickers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill prices.csv for all Ibovespa tickers")
    parser.add_argument("--dry-run", action="store_true", help="List missing tickers only")
    parser.add_argument("--pause", type=float, default=0.5, help="Seconds between API calls")
    args = parser.parse_args(argv)

    tickers = list_tickers()
    if not tickers:
        print("No universe loaded. Run: decifra sync universe", file=sys.stderr)
        return 1

    print(f"Universe: {len(tickers)} tickers")
    print(f"BRAPI_API_KEY: {'set' if BRAPI_API_KEY else 'NOT set (using yfinance fallback)'}")

    missing = []
    existing = []
    for t in tickers:
        prices_path = company_dir(t) / "financials" / "prices.csv"
        if prices_path.exists() and prices_path.stat().st_size > 100:
            existing.append(t)
        else:
            missing.append(t)

    print(f"Existing prices: {len(existing)}/{len(tickers)}")
    print(f"Missing prices:  {len(missing)}/{len(tickers)}")

    if args.dry_run:
        print(f"\n[DRY-RUN] Would backfill: {', '.join(missing)}")
        return 0

    if not missing:
        print("All tickers already have prices.csv — nothing to do.")
        return 0

    print(f"\nBackfilling {len(missing)} tickers...")
    success = []
    failed = []
    for i, t in enumerate(missing, 1):
        print(f"  [{i}/{len(missing)}] {t}...", end=" ", flush=True)
        try:
            result = sync_prices(t)
            if result:
                size = result.stat().st_size
                print(f"OK ({size:,} bytes)")
                success.append(t)
            else:
                print("EMPTY (no data returned)")
                failed.append(t)
        except Exception as e:
            print(f"ERROR: {e}")
            failed.append(t)
        if i < len(missing):
            time.sleep(args.pause)

    print(f"\nBackfill complete: {len(success)} succeeded, {len(failed)} failed/empty")
    if failed:
        print(f"Failed: {', '.join(failed)}")

    # Spot-check PETR4/VALE3/ITUB4
    print("\n--- Spot checks ---")
    for ticker in ("PETR4", "VALE3", "ITUB4"):
        path = company_dir(ticker) / "financials" / "prices.csv"
        if path.exists():
            import pandas as pd
            df = pd.read_csv(path)
            print(f"  {ticker}: {len(df)} rows, columns={list(df.columns[:5])}")
        else:
            print(f"  {ticker}: NO prices.csv")

    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
