from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

from decifra.store.folders import company_dir

# Qualitative risk keywords (Portuguese + English)
RISK_KEYWORDS: list[str] = [
    "reestruturacao",
    "reestruturação",
    "recuperacao judicial",
    "recuperação judicial",
    "default",
    "downgrade",
    "covenant",
    "adiamento",
    "impairment",
    "perda",
    "inadimplencia",
    "inadimplência",
    "falencia",
    "falência",
    "renegociacao de divida",
    "renegociação de dívida",
    "going concern",
    "continuidade operacional",
]

MAX_PENALTY = 15.0
POINTS_PER_HIT = 3.0
LOOKBACK_DAYS = 730  # ~24 months


def _strip_accents(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm(text: str) -> str:
    return _strip_accents(str(text or "")).lower()


def _normalized_keywords() -> list[str]:
    # Deduplicate after accent stripping
    seen: set[str] = set()
    out: list[str] = []
    for kw in RISK_KEYWORDS:
        n = _norm(kw)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def _parse_date(value: str) -> datetime | None:
    s = str(value or "").strip()
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), tzinfo=timezone.utc)
    return None


def _within_lookback(dt: datetime | None, cutoff: datetime) -> bool:
    if dt is None:
        return True  # keep undated rows; still useful signal
    return dt >= cutoff


def _find_keyword_hits(text: str, keywords: list[str]) -> list[str]:
    n = _norm(text)
    return [kw for kw in keywords if kw in n]


def scan_qualitative_signals(
    ticker: str,
    *,
    lookback_days: int = LOOKBACK_DAYS,
    max_penalty: float = MAX_PENALTY,
    points_per_hit: float = POINTS_PER_HIT,
) -> dict[str, Any]:
    """Scan notices/transcripts for risk keywords; return capped penalty and hit details."""
    root = company_dir(ticker)
    keywords = _normalized_keywords()
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    hits: list[dict[str, Any]] = []
    matched_keywords: set[str] = set()

    notices_path = root / "notices" / "index.csv"
    if notices_path.exists():
        df = pd.read_csv(notices_path, dtype=str).fillna("")
        for _, row in df.iterrows():
            dt = _parse_date(row.get("date", ""))
            if not _within_lookback(dt, cutoff):
                continue
            blob = " ".join(
                str(row.get(c, "")) for c in ("title", "category", "source") if c in row.index
            )
            found = _find_keyword_hits(blob, keywords)
            if found:
                matched_keywords.update(found)
                hits.append(
                    {
                        "source": "notice",
                        "date": row.get("date", ""),
                        "title": row.get("title", ""),
                        "keywords": found,
                        "path": row.get("local_path", ""),
                        "url": row.get("source_url", ""),
                    }
                )

    transcripts_index = root / "transcripts" / "index.csv"
    if transcripts_index.exists():
        df = pd.read_csv(transcripts_index, dtype=str).fillna("")
        for _, row in df.iterrows():
            dt = _parse_date(row.get("date", ""))
            if not _within_lookback(dt, cutoff):
                continue
            blob = " ".join(str(row.get(c, "")) for c in ("title", "category") if c in row.index)
            text_rel = row.get("text_path") or ""
            if text_rel:
                tp = root / text_rel
                if tp.exists():
                    # Cap read size for speed
                    blob += " " + tp.read_text(encoding="utf-8", errors="ignore")[:50000]
            found = _find_keyword_hits(blob, keywords)
            if found:
                matched_keywords.update(found)
                hits.append(
                    {
                        "source": "transcript",
                        "date": row.get("date", ""),
                        "title": row.get("title", ""),
                        "keywords": found,
                        "path": text_rel or row.get("local_path", ""),
                        "url": row.get("source_url", ""),
                    }
                )

    # Also scan loose text files not already covered
    text_dir = root / "transcripts" / "text"
    if text_dir.exists():
        known = {h.get("path") for h in hits}
        for tp in text_dir.glob("*.txt"):
            rel = str(tp.relative_to(root))
            if rel in known:
                continue
            text = tp.read_text(encoding="utf-8", errors="ignore")[:50000]
            found = _find_keyword_hits(text, keywords)
            if found:
                matched_keywords.update(found)
                hits.append(
                    {
                        "source": "transcript_text",
                        "date": "",
                        "title": tp.name,
                        "keywords": found,
                        "path": rel,
                        "url": "",
                    }
                )

    # Penalty based on distinct keyword matches + document count, capped
    doc_hits = len(hits)
    kw_hits = len(matched_keywords)
    raw = points_per_hit * min(doc_hits, 5) + 1.0 * kw_hits
    penalty = min(max_penalty, float(raw))

    return {
        "ticker": ticker.upper(),
        "qualitative_penalty": penalty,
        "signal_hit_count": doc_hits,
        "matched_keywords": sorted(matched_keywords),
        "signal_hits": hits[:40],
    }


def format_signal_summary(scan: dict[str, Any]) -> str:
    kws = scan.get("matched_keywords") or []
    n = scan.get("signal_hit_count") or 0
    if not n:
        return ""
    return f"{n} docs; keywords: {', '.join(kws[:8])}"
