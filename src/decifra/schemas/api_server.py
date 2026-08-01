"""Read-only lake API for the React Terminal Dark UI (IMP-037).

Uses the stdlib HTTP server — no FastAPI dependency.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from decifra.http_util import normalize_ticker
from decifra.schemas.assemble import (
    assemble_company_profile,
    assemble_credit_debt_matrix,
    assemble_valuation_waterfall,
)
from decifra.credit.assemble_models import assemble_capacity
from decifra.credit.metrics import extract_kpis
from decifra.schemas.screener import assemble_catalyst_feed, assemble_opportunity_screener
from decifra.store.folders import list_tickers
from decifra.valuation.dcf import _CVM_THOUSANDS_SCALE


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


def _debt_matrix_live(ticker: str) -> dict[str, Any]:
    pack = assemble_capacity(ticker)
    inputs = pack.get("inputs") or {}
    return assemble_credit_debt_matrix(
        ticker,
        net_debt=inputs.get("net_debt"),
        ebitda=inputs.get("ebitda"),
        ocf=inputs.get("ocf"),
        debt_service=inputs.get("debt_service"),
    )


def _waterfall_live(ticker: str) -> dict[str, Any]:
    kpis = extract_kpis(ticker)
    ocf = kpis.get("operating_cf")
    interest = kpis.get("interest_expense")
    if ocf is not None:
        ocf = abs(float(ocf)) * _CVM_THOUSANDS_SCALE
    else:
        ocf = 0.0
    if interest is not None:
        interest = abs(float(interest)) * _CVM_THOUSANDS_SCALE
    else:
        interest = 0.0
    amort = 0.0
    return assemble_valuation_waterfall(ticker, ocf=ocf, interest=interest, amortization=amort)


def handle_api(path: str, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
    if path in ("/api/health", "/health"):
        return 200, {"ok": True, "service": "decifra-lake-api"}

    if path in ("/api/screener", "/api/opportunity_screener"):
        tickers = query.get("tickers", [None])[0]
        limit_raw = (query.get("limit") or [None])[0]
        limit = int(limit_raw) if limit_raw else None
        names = [normalize_ticker(x) for x in tickers.split(",")] if tickers else None
        return 200, assemble_opportunity_screener(names, limit=limit)

    if path in ("/api/catalysts", "/api/catalyst_feed"):
        limit_raw = (query.get("limit") or ["12"])[0]
        screener = assemble_opportunity_screener(limit=int(limit_raw))
        return 200, assemble_catalyst_feed(screener)

    if path.startswith("/api/profile/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        return 200, assemble_company_profile(ticker)

    if path.startswith("/api/debt/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        return 200, _debt_matrix_live(ticker)

    if path.startswith("/api/waterfall/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        return 200, _waterfall_live(ticker)

    if path == "/api/tickers":
        return 200, {"tickers": list_tickers()}

    return 404, {"error": "not_found", "path": path}


class LakeAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:  # quieter default
        pass

    def _send(self, code: int, payload: dict[str, Any]) -> None:
        body = _json_bytes(payload)
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        code, payload = handle_api(parsed.path, query)
        self._send(code, payload)


def serve_lake_api(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), LakeAPIHandler)
    print(f"decifra lake API on http://{host}:{port}  (Ctrl+C to stop)")
    server.serve_forever()


def export_ui_bundle(
    out_dir,
    *,
    tickers: list[str] | None = None,
    limit: int = 8,
    detail_ticker: str = "PETR4",
) -> dict[str, Any]:
    """Write React-consumable JSON (screener + catalysts + schema trio) from the lake."""
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    screener = assemble_opportunity_screener(tickers, limit=limit)
    catalysts = assemble_catalyst_feed(screener)
    profile = assemble_company_profile(detail_ticker)
    debt = _debt_matrix_live(detail_ticker)
    waterfall = _waterfall_live(detail_ticker)
    written = {}
    for name, payload in (
        ("opportunity_screener.json", screener),
        ("catalyst_feed.json", catalysts),
        ("company_profile.json", profile),
        ("credit_debt_matrix.json", debt),
        ("valuation_waterfall.json", waterfall),
    ):
        path = out / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        written[name] = str(path)
    return written
