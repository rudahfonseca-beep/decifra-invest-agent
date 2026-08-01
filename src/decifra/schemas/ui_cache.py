"""In-process TTL caches + disk-backed warm artifacts for lake API payloads."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, TypeVar

from decifra.config import UI_CACHE_DIR, ensure_dirs

T = TypeVar("T")

# Screener/catalyst assemblies are expensive (APV+Merton+capacity per ticker).
DEFAULT_TTL_SECONDS = 300.0

_CREDIT_DFS: dict[str, Any] = {}
_TTL_CACHE: dict[str, tuple[float, Any]] = {}


def credit_cache_key(*, include_signals: bool, scope: str = "all") -> str:
    return f"sig={include_signals}:scope={scope}"


def get_cached_credit_df(*, include_signals: bool, scope: str = "all") -> Any | None:
    return _CREDIT_DFS.get(credit_cache_key(include_signals=include_signals, scope=scope))


def set_cached_credit_df(*, include_signals: bool, scope: str = "all", df: Any) -> None:
    _CREDIT_DFS[credit_cache_key(include_signals=include_signals, scope=scope)] = df


def clear_credit_cache() -> None:
    _CREDIT_DFS.clear()


def ttl_get(key: str) -> Any | None:
    hit = _TTL_CACHE.get(key)
    if hit is None:
        return None
    expires_at, value = hit
    if time.monotonic() > expires_at:
        _TTL_CACHE.pop(key, None)
        return None
    return value


def ttl_set(key: str, value: Any, *, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
    _TTL_CACHE[key] = (time.monotonic() + ttl_seconds, value)


def ttl_get_or_set(
    key: str,
    factory: Callable[[], T],
    *,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    refresh: bool = False,
) -> T:
    if not refresh:
        cached = ttl_get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
    value = factory()
    ttl_set(key, value, ttl_seconds=ttl_seconds)
    return value


def clear_ttl_cache() -> None:
    _TTL_CACHE.clear()


def clear_all_ui_caches() -> None:
    clear_credit_cache()
    clear_ttl_cache()


def disk_cache_path(name: str) -> Path:
    ensure_dirs()
    safe = name.replace("/", "_").replace(":", "_")
    if not safe.endswith(".json"):
        safe = f"{safe}.json"
    return UI_CACHE_DIR / safe


def disk_read(name: str) -> Any | None:
    path = disk_cache_path(name)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def disk_write(name: str, value: Any) -> Path:
    path = disk_cache_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return path


def disk_get_or_set(
    name: str,
    factory: Callable[[], T],
    *,
    memory_key: str | None = None,
    ttl_seconds: float = DEFAULT_TTL_SECONDS,
    refresh: bool = False,
) -> T:
    """Memory TTL → disk JSON → factory; persists factory result to disk."""
    mem_key = memory_key or f"disk:{name}"
    if not refresh:
        hit = ttl_get(mem_key)
        if hit is not None:
            return hit  # type: ignore[return-value]
        disk_hit = disk_read(name)
        if disk_hit is not None:
            ttl_set(mem_key, disk_hit, ttl_seconds=ttl_seconds)
            return disk_hit  # type: ignore[return-value]
    value = factory()
    ttl_set(mem_key, value, ttl_seconds=ttl_seconds)
    try:
        disk_write(name, value)
    except OSError:
        pass
    return value


def warm_ui_disk_cache(*, scope: str = "core", screener_limit: int | None = None) -> dict[str, str]:
    """Compute and persist core UI payloads under data/cache/ui/."""
    from decifra.schemas.research_api import (
        coverage_payload,
        credit_table_payload,
        industries_payload,
        tickers_payload,
    )
    from decifra.schemas.screener import assemble_catalyst_feed, assemble_opportunity_screener

    written: dict[str, str] = {}
    clear_ttl_cache()

    screener = assemble_opportunity_screener(
        scope=scope, limit=screener_limit, refresh=True, persist_disk=True
    )
    written["screener_core.json"] = str(disk_cache_path(f"screener_{scope}"))
    catalysts = assemble_catalyst_feed(screener, refresh=True)
    disk_write("catalysts_core", catalysts)
    written["catalysts_core.json"] = str(disk_cache_path("catalysts_core"))

    credit = credit_table_payload(
        include_signals=False, show_incomplete=True, scope=scope, refresh=True
    )
    disk_write("credit_fundamentals", credit)
    written["credit_fundamentals.json"] = str(disk_cache_path("credit_fundamentals"))

    industries = industries_payload(include_signals=False, scope=scope)
    disk_write("industries", industries)
    written["industries.json"] = str(disk_cache_path("industries"))

    tickers = tickers_payload(
        include_signals=False, show_incomplete=True, scope=scope, limit=500
    )
    disk_write("tickers", tickers)
    written["tickers.json"] = str(disk_cache_path("tickers"))

    coverage = coverage_payload(scope=scope)
    disk_write("coverage", coverage)
    written["coverage.json"] = str(disk_cache_path("coverage"))
    return written
