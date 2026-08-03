"""Lake API for the React Terminal Dark UI (GET research + POST sync/report)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from decifra.credit.assemble_models import assemble_capacity
from decifra.credit.metrics import extract_kpis
from decifra.http_util import normalize_ticker
from decifra.schemas.assemble import (
    assemble_company_profile,
    assemble_credit_debt_matrix,
    assemble_valuation_waterfall,
)
from decifra.schemas.research_api import (
    coverage_payload,
    credit_detail_payload,
    credit_table_payload,
    industries_payload,
    report_build_payload,
    report_catalog_payload,
    tickers_payload,
    valuation_defaults_payload,
    valuation_run_payload,
)
from decifra.schemas.screener import assemble_catalyst_feed, assemble_opportunity_screener
from decifra.schemas.ui_cache import ttl_get_or_set
from decifra.store.folders import list_tickers
from decifra.valuation.dcf import _CVM_THOUSANDS_SCALE


def _json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")


def _bool(qs: dict[str, list[str]], key: str, default: bool = False) -> bool:
    raw = (qs.get(key) or [None])[0]
    if raw is None:
        return default
    return str(raw).lower() in ("1", "true", "yes", "on")


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
    return assemble_valuation_waterfall(ticker, ocf=ocf, interest=interest, amortization=0.0)


def _int(qs: dict[str, list[str]], key: str, default: int | None = None) -> int | None:
    raw = (qs.get(key) or [None])[0]
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def _scope(qs: dict[str, list[str]], default: str = "core") -> str:
    raw = ((qs.get("scope") or [default])[0] or default).strip().lower()
    return raw if raw in ("all", "core") else default


def handle_api(path: str, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
    if path in ("/api/health", "/health"):
        return 200, {"ok": True, "service": "decifra-lake-api"}

    if path in ("/api/screener", "/api/opportunity_screener"):
        tickers = query.get("tickers", [None])[0]
        limit = _int(query, "limit")
        offset = _int(query, "offset", 0) or 0
        scope = _scope(query, "core")
        q = (query.get("q") or [None])[0]
        names = [normalize_ticker(x) for x in tickers.split(",")] if tickers else None
        return 200, assemble_opportunity_screener(
            names,
            limit=limit,
            offset=offset,
            refresh=_bool(query, "refresh", False),
            scope=scope,
            q=q,
        )

    if path in ("/api/catalysts", "/api/catalyst_feed"):
        limit = _int(query, "limit", 12) or 12
        refresh = _bool(query, "refresh", False)
        scope = _scope(query, "core")
        # Reuse screener TTL entry so /api/screener + /api/catalysts share one build.
        screener = assemble_opportunity_screener(limit=limit, refresh=refresh, scope=scope)
        return 200, assemble_catalyst_feed(screener, limit=limit, refresh=refresh, scope=scope)

    if path.startswith("/api/profile/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        refresh = _bool(query, "refresh", False)
        return 200, ttl_get_or_set(
            f"profile:{ticker}",
            lambda: assemble_company_profile(ticker),
            refresh=refresh,
        )

    if path.startswith("/api/debt/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        refresh = _bool(query, "refresh", False)
        return 200, ttl_get_or_set(
            f"debt:{ticker}",
            lambda: _debt_matrix_live(ticker),
            refresh=refresh,
        )

    if path.startswith("/api/waterfall/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        refresh = _bool(query, "refresh", False)
        return 200, ttl_get_or_set(
            f"waterfall:{ticker}",
            lambda: _waterfall_live(ticker),
            refresh=refresh,
        )

    if path == "/api/credit":
        return 200, credit_table_payload(
            industry=(query.get("industry") or [None])[0],
            cohort=(query.get("cohort") or [None])[0],
            include_signals=_bool(query, "signals", False),
            show_incomplete=_bool(query, "incomplete", False),
            refresh=_bool(query, "refresh", False),
            scope=_scope(query, "core"),
            q=(query.get("q") or [None])[0],
            limit=_int(query, "limit"),
            offset=_int(query, "offset", 0) or 0,
        )

    if path.startswith("/api/credit/"):
        ticker = normalize_ticker(path.rsplit("/", 1)[-1])
        return 200, credit_detail_payload(
            ticker, include_signals=_bool(query, "signals", False)
        )

    if path == "/api/industries":
        return 200, industries_payload(
            include_signals=_bool(query, "signals", False),
            scope=_scope(query, "core"),
        )

    if path == "/api/tickers":
        scope = _scope(query, "core")
        # Rich ticker list (credit-enriched); plain universe list via ?plain=1
        if _bool(query, "plain", False):
            return 200, {
                "tickers": list_tickers(scope=scope),  # type: ignore[arg-type]
                "scope": scope,
                "count": len(list_tickers(scope=scope)),  # type: ignore[arg-type]
            }
        return 200, tickers_payload(
            industry=(query.get("industry") or [None])[0],
            include_signals=_bool(query, "signals", False),
            show_incomplete=_bool(query, "incomplete", True),
            scope=scope,
            q=(query.get("q") or [None])[0],
            limit=_int(query, "limit"),
            offset=_int(query, "offset", 0) or 0,
        )

    if path == "/api/coverage":
        return 200, coverage_payload(scope=_scope(query, "all"))

    if path == "/api/valuation/defaults":
        ticker = (query.get("ticker") or [None])[0]
        if not ticker:
            return 400, {"error": "ticker required"}
        peers_raw = (query.get("peers") or [""])[0]
        peers = [p for p in peers_raw.split(",") if p.strip()] if peers_raw else None
        return 200, valuation_defaults_payload(ticker, peers)

    if path == "/api/valuation/run":
        ticker = (query.get("ticker") or [None])[0]
        if not ticker:
            return 400, {"error": "ticker required"}
        peers_raw = (query.get("peers") or [""])[0]
        peers = [p for p in peers_raw.split(",") if p.strip()] if peers_raw else []
        stat = (query.get("stat") or ["median"])[0]
        return 200, valuation_run_payload(
            ticker,
            peers=peers,
            multiples_stat=stat,
            include_sensitivity=_bool(query, "sensitivity", True),
        )

    if path == "/api/report/catalog":
        return 200, report_catalog_payload()

    return 404, {"error": "not_found", "path": path}


def handle_api_post(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    if path == "/api/valuation/run":
        ticker = body.get("ticker")
        if not ticker:
            return 400, {"error": "ticker required"}
        return 200, valuation_run_payload(
            str(ticker),
            peers=list(body.get("peers") or []),
            assumptions=body.get("assumptions"),
            multiples_stat=str(body.get("stat") or "median"),
            include_sensitivity=bool(body.get("sensitivity", True)),
        )

    if path == "/api/report/build":
        result = report_build_payload(body)
        return (200 if result.get("ok") else 400), result

    if path in ("/api/sync/financials", "/api/sync/financials/"):
        return _sync_financials_post(body)

    if path in ("/api/watchlist", "/api/watchlist/"):
        return _watchlist_post(body)

    return 404, {
        "error": (
            "not_found — lake API has no route for this path. "
            "Restart `decifra schemas serve` so /api/sync/financials is loaded "
            f"(got path={path!r})."
        ),
        "path": path,
    }


def _sync_financials_post(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """POST body: { tickers: string[], year_from?: int, year_to?: int, include_prices?: bool }."""
    from decifra.config import DEFAULT_FINANCIAL_YEARS
    from decifra.cvm.financials import sync_financials

    raw_tickers = body.get("tickers") or body.get("ticker")
    if isinstance(raw_tickers, str):
        names = [raw_tickers]
    elif isinstance(raw_tickers, list):
        names = [str(t) for t in raw_tickers]
    else:
        return 400, {"error": "tickers required (list of equity codes)"}

    names = [normalize_ticker(t) for t in names if str(t).strip()]
    if not names:
        return 400, {"error": "tickers required (list of equity codes)"}

    y_from = body.get("year_from", body.get("from"))
    y_to = body.get("year_to", body.get("to"))
    if y_from is None and y_to is None:
        years = list(DEFAULT_FINANCIAL_YEARS)
    else:
        try:
            start = int(y_from if y_from is not None else y_to)
            end = int(y_to if y_to is not None else y_from)
        except (TypeError, ValueError):
            return 400, {"error": "year_from / year_to must be integers"}
        if start > end:
            start, end = end, start
        if start < 2000 or end > 2035:
            return 400, {"error": "years must be between 2000 and 2035"}
        years = list(range(start, end + 1))

    include_prices = bool(body.get("include_prices", True))
    add_to_watchlist = bool(body.get("add_to_watchlist", True))
    try:
        result = sync_financials(
            tickers=names,
            years=years,
            include_prices=include_prices,
        )
    except Exception as exc:
        return 500, {"ok": False, "error": str(exc)}

    # Credit / UI memory caches may be stale after new financial CSVs.
    try:
        from decifra.schemas.ui_cache import clear_all_ui_caches

        clear_all_ui_caches()
    except Exception:
        pass

    written = result.get("written") or {}
    watchlist_info: dict[str, Any] | None = None
    if add_to_watchlist:
        wl_code, wl_payload = _watchlist_post({"tickers": names})
        if wl_code == 200:
            watchlist_info = wl_payload

    return 200, {
        "ok": True,
        "tickers": names,
        "years": years,
        "cnpj_mapped": result.get("cnpj_mapped"),
        "ticker_count": result.get("tickers"),
        "written": {t: written.get(t, []) for t in names},
        "watchlist": watchlist_info,
        "coverage": coverage_payload(scope="all"),
    }


def _watchlist_post(body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """POST body: { tickers: string[] } — append to watchlist.json (promotes to core scope)."""
    import json
    from pathlib import Path

    from decifra.config import WATCHLIST_JSON, ensure_dirs
    from decifra.store.folders import load_meta, load_universe, save_meta
    from decifra.universe.listed import load_watchlist

    raw = body.get("tickers") or body.get("ticker")
    if isinstance(raw, str):
        names = [raw]
    elif isinstance(raw, list):
        names = [str(t) for t in raw]
    else:
        return 400, {"error": "tickers required"}

    names = [normalize_ticker(t) for t in names if str(t).strip()]
    if not names:
        return 400, {"error": "tickers required"}

    ensure_dirs()
    existing = load_watchlist()
    added: list[str] = []
    for t in names:
        if t not in existing:
            existing.append(t)
            added.append(t)

    path = Path(WATCHLIST_JSON)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"tickers": existing}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Patch equities.json + meta sync_tier so caches/export stay consistent.
    try:
        data = load_universe()
        by_ticker = {
            normalize_ticker(c.get("ticker") or ""): c for c in data.get("constituents", [])
        }
        for t in names:
            if t in by_ticker:
                by_ticker[t]["sync_tier"] = "core"
            meta = load_meta(t)
            meta["sync_tier"] = "core"
            save_meta(t, meta)
        from decifra.config import EQUITIES_JSON

        if EQUITIES_JSON.exists():
            EQUITIES_JSON.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception:
        pass

    try:
        from decifra.schemas.ui_cache import clear_all_ui_caches

        clear_all_ui_caches()
    except Exception:
        pass

    return 200, {
        "ok": True,
        "watchlist": existing,
        "added": added,
        "count": len(existing),
    }


class LakeAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        import traceback

        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            code, payload = handle_api(parsed.path, query)
            self._send(code, payload)
        except Exception as exc:
            self._send(
                500,
                {"error": str(exc), "traceback": traceback.format_exc()},
            )

    def do_POST(self) -> None:  # noqa: N802
        import traceback

        try:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._send(400, {"error": "invalid_json"})
                return
            if not isinstance(body, dict):
                self._send(400, {"error": "body must be object"})
                return
            code, payload = handle_api_post(parsed.path, body)
            self._send(code, payload)
        except Exception as exc:
            self._send(
                500,
                {"error": str(exc), "traceback": traceback.format_exc()},
            )


def serve_lake_api(host: str = "127.0.0.1", port: int = 8765) -> None:
    # Warm fundamental credit + disk UI caches so first UI clicks are fast.
    try:
        from decifra.schemas.research_api import get_credit_df
        from decifra.schemas.ui_cache import disk_read, ttl_set

        print("Warming credit table cache (core fundamentals, no signal scan)…")
        get_credit_df(include_signals=False, scope="core")
        for name, mem_key in (
            ("screener_core", "disk:screener_core"),
            ("tickers", "disk:tickers"),
            ("industries", "disk:industries"),
            ("credit_fundamentals", "disk:credit_fundamentals"),
        ):
            payload = disk_read(name)
            if payload is not None:
                ttl_set(mem_key, payload)
        print("Cache ready.")
    except Exception as exc:
        print(f"Cache warm skipped: {exc}")
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
    """Write React-consumable JSON from the lake (schemas + research tables)."""
    from pathlib import Path

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    screener = assemble_opportunity_screener(tickers, limit=limit, scope="core")
    catalysts = assemble_catalyst_feed(screener, scope="core")
    profile = assemble_company_profile(detail_ticker)
    debt = _debt_matrix_live(detail_ticker)
    waterfall = _waterfall_live(detail_ticker)
    credit = credit_table_payload(
        include_signals=False, show_incomplete=True, scope="core"
    )
    industries = industries_payload(scope="core")
    tickers_rich = tickers_payload(show_incomplete=True, scope="core")
    coverage = coverage_payload(scope="all")
    written = {}
    for name, payload in (
        ("opportunity_screener.json", screener),
        ("catalyst_feed.json", catalysts),
        ("company_profile.json", profile),
        ("credit_debt_matrix.json", debt),
        ("valuation_waterfall.json", waterfall),
        ("credit_table.json", credit),
        ("industries.json", industries),
        ("tickers.json", tickers_rich),
        ("coverage.json", coverage),
    ):
        path = out / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        written[name] = str(path)
    return written
