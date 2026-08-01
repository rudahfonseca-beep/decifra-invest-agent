"""SEC EDGAR best-effort fund/issuer exposure (fixture-friendly)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import FUNDS_DIR, ensure_dirs
from decifra.http_util import USER_AGENT, client

EDGAR_COMPANY_SEARCH = "https://efts.sec.gov/LATEST/search-index"


def sample_edgar_exposure() -> list[dict[str, Any]]:
    return [
        {
            "issuer": "Petroleo Brasileiro S.A. - Petrobras",
            "ticker": "PBR",
            "cik": "0001119639",
            "form": "20-F",
            "note": "ADR / foreign issuer exposure sample",
            "source": "EDGAR",
            "lineage": {"source_doc": "SEC EDGAR sample"},
        }
    ]


def sync_edgar(
    *,
    query: str | None = None,
    use_network: bool = False,
    write_fixture_if_missing: bool = True,
) -> dict[str, Any]:
    """Write ADR/foreign exposure snapshot under ``data/funds/edgar/``."""
    ensure_dirs()
    out_dir = FUNDS_DIR / "edgar"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "exposure.json"
    rows: list[dict[str, Any]] = []
    errors: list[str] = []

    if use_network and query:
        try:
            with client() as c:
                # Lightweight ping — full EFTS query APIs change; keep best-effort.
                resp = c.get(
                    "https://www.sec.gov/cgi-bin/browse-edgar",
                    params={"action": "getcompany", "company": query, "output": "atom", "count": 5},
                    headers={"User-Agent": USER_AGENT},
                )
                if resp.status_code == 200 and resp.text:
                    rows.append(
                        {
                            "query": query,
                            "status": resp.status_code,
                            "bytes": len(resp.content),
                            "source": "EDGAR",
                            "lineage": {"source_doc": "browse-edgar atom"},
                        }
                    )
                else:
                    errors.append(f"EDGAR HTTP {resp.status_code}")
        except Exception as exc:
            errors.append(str(exc))

    if not rows and (write_fixture_if_missing or path.exists()):
        if path.exists() and not write_fixture_if_missing:
            rows = json.loads(path.read_text(encoding="utf-8")).get("exposures", [])
        else:
            rows = sample_edgar_exposure()

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "exposures": rows,
        "errors": errors,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path), "count": len(rows), "errors": errors}
