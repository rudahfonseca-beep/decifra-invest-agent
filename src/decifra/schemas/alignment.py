"""Align ITR DT_REFER with debt schedule reference dates."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def align_itr_debt_dates(
    statement_dates: list[str],
    debt_dates: list[str],
    *,
    max_days: int = 45,
) -> dict[str, Any]:
    """Pair each statement DT_REFER with the nearest debt schedule date.

    Returns matches and unmatched sides for credit/valuation readers.
    """
    stmt = [(d, _parse_date(d)) for d in statement_dates]
    debt = [(d, _parse_date(d)) for d in debt_dates]
    matches: list[dict[str, Any]] = []
    used_debt: set[str] = set()

    for s_raw, s_dt in stmt:
        if s_dt is None:
            matches.append(
                {
                    "statement_dt_refer": s_raw,
                    "debt_dt_refer": None,
                    "delta_days": None,
                    "aligned": False,
                }
            )
            continue
        best = None
        best_delta = None
        for d_raw, d_dt in debt:
            if d_dt is None or d_raw in used_debt:
                continue
            delta = abs((s_dt - d_dt).days)
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best = d_raw
        aligned = best is not None and best_delta is not None and best_delta <= max_days
        if aligned and best is not None:
            used_debt.add(best)
        matches.append(
            {
                "statement_dt_refer": s_raw,
                "debt_dt_refer": best if aligned else None,
                "delta_days": best_delta if aligned else None,
                "aligned": aligned,
            }
        )

    return {
        "matches": matches,
        "max_days": max_days,
        "lineage": {"source_doc": "ITR_DT_REFER_alignment"},
    }
