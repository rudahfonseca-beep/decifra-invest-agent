from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from decifra.config import CVM_CACHE_DIR, ensure_dirs
from decifra.http_util import download_to_file


def cached_zip_path(name: str) -> Path:
    ensure_dirs()
    return CVM_CACHE_DIR / name


def ensure_zip(url: str, filename: str, *, force: bool = False) -> Path:
    dest = cached_zip_path(filename)
    return download_to_file(url, dest, force=force)


def read_csv_from_zip(
    zip_path: Path,
    member_substr: str,
    *,
    sep: str = ";",
    encoding: str = "latin-1",
) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if member_substr.lower() in n.lower() and n.lower().endswith(".csv")]
        if not names:
            raise FileNotFoundError(f"No CSV matching '{member_substr}' in {zip_path.name}")
        # Prefer exact-ish shortest match
        names.sort(key=len)
        with zf.open(names[0]) as fh:
            raw = fh.read()
    return pd.read_csv(io.BytesIO(raw), sep=sep, encoding=encoding, dtype=str, low_memory=False)


def list_zip_members(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as zf:
        return zf.namelist()


def read_all_matching_csvs(
    zip_path: Path,
    member_substr: str,
    *,
    sep: str = ";",
    encoding: str = "latin-1",
) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if member_substr.lower() in n.lower() and n.lower().endswith(".csv")]
        for name in names:
            with zf.open(name) as fh:
                frames.append(
                    pd.read_csv(io.BytesIO(fh.read()), sep=sep, encoding=encoding, dtype=str, low_memory=False)
                )
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
