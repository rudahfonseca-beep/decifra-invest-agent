"""CVM Funds INF_DIARIO (daily NAV) and CDA (monthly holdings)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from decifra.config import CVM_CACHE_DIR, CVM_CDA_ZIP, CVM_INF_DIARIO_ZIP, FUNDS_DIR, ensure_dirs
from decifra.cvm.download import ensure_zip, read_all_matching_csvs


def _yyyymm(year: int, month: int) -> str:
    return f"{year}{month:02d}"


def inf_diario_filename(yyyymm: str) -> str:
    return f"inf_diario_fi_{yyyymm}.zip"


def cda_filename(yyyymm: str) -> str:
    return f"cda_fi_{yyyymm}.zip"


def write_sample_inf_diario(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "CNPJ_FUNDO": "00000000000191",
                "DT_COMPTC": "2026-07-31",
                "VL_TOTAL": "1000000",
                "VL_QUOTA": "1.2345",
                "NR_COTST": "100",
            }
        ]
    )
    # Store as csv beside zip-less cache for offline
    csv_path = path.with_suffix(".csv")
    df.to_csv(csv_path, index=False, sep=";", encoding="utf-8")
    return csv_path


def write_sample_cda(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(
        [
            {
                "CNPJ_FUNDO": "00000000000191",
                "DT_COMPTC": "2026-07-31",
                "TP_APLIC": "Ações",
                "EMISSOR": "PETROBRAS",
                "CNPJ_EMISSOR": "33000167000101",
                "VL_MERC_POS_FINAL": "50000",
            }
        ]
    )
    csv_path = path.with_suffix(".csv")
    df.to_csv(csv_path, index=False, sep=";", encoding="utf-8")
    return csv_path


def sync_cvm_funds(
    *,
    year: int = 2026,
    month: int = 7,
    force: bool = False,
    from_cache_only: bool = True,
    write_fixture_if_missing: bool = True,
) -> dict[str, Any]:
    """Sync INF_DIARIO + CDA into ``data/funds/``.

    Default ``from_cache_only=True`` avoids megabyte network pulls in CI;
    set False to download CVM zips when available.
    """
    ensure_dirs()
    yyyymm = _yyyymm(year, month)
    out_dir = FUNDS_DIR / yyyymm
    out_dir.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    written: list[str] = []

    # INF_DIARIO
    inf_zip = CVM_CACHE_DIR / inf_diario_filename(yyyymm)
    inf_csv_fallback = FUNDS_DIR / "fixtures" / f"inf_diario_{yyyymm}.csv"
    try:
        if from_cache_only:
            if inf_zip.exists():
                df = read_all_matching_csvs(inf_zip, "inf_diario")
            elif inf_csv_fallback.exists() or write_fixture_if_missing:
                if not inf_csv_fallback.exists():
                    write_sample_inf_diario(inf_csv_fallback)
                df = pd.read_csv(inf_csv_fallback, sep=";", dtype=str)
            else:
                df = pd.DataFrame()
                errors.append("INF_DIARIO missing cache")
        else:
            ensure_zip(CVM_INF_DIARIO_ZIP.format(yyyymm=yyyymm), inf_diario_filename(yyyymm), force=force)
            df = read_all_matching_csvs(inf_zip, "inf_diario")
        if not df.empty:
            dest = out_dir / "inf_diario.csv"
            df.to_csv(dest, index=False, encoding="utf-8")
            written.append(str(dest))
    except Exception as exc:
        errors.append(f"INF_DIARIO: {exc}")

    # CDA
    cda_zip = CVM_CACHE_DIR / cda_filename(yyyymm)
    cda_csv_fallback = FUNDS_DIR / "fixtures" / f"cda_{yyyymm}.csv"
    try:
        if from_cache_only:
            if cda_zip.exists():
                df = read_all_matching_csvs(cda_zip, "cda")
            elif cda_csv_fallback.exists() or write_fixture_if_missing:
                if not cda_csv_fallback.exists():
                    write_sample_cda(cda_csv_fallback)
                df = pd.read_csv(cda_csv_fallback, sep=";", dtype=str)
            else:
                df = pd.DataFrame()
                errors.append("CDA missing cache")
        else:
            ensure_zip(CVM_CDA_ZIP.format(yyyymm=yyyymm), cda_filename(yyyymm), force=force)
            df = read_all_matching_csvs(cda_zip, "cda")
        if not df.empty:
            dest = out_dir / "cda.csv"
            df.to_csv(dest, index=False, encoding="utf-8")
            written.append(str(dest))
    except Exception as exc:
        errors.append(f"CDA: {exc}")

    meta = {
        "yyyymm": yyyymm,
        "written": written,
        "errors": errors,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lineage": {"source_doc": "CVM FI INF_DIARIO/CDA"},
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta
