"""In-process TTL caches for lake API payloads (credit DF, screener, catalysts)."""

from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Screener/catalyst assemblies are expensive (APV+Merton+capacity per ticker).
DEFAULT_TTL_SECONDS = 300.0

_CREDIT_DFS: dict[str, Any] = {}
_TTL_CACHE: dict[str, tuple[float, Any]] = {}


def credit_cache_key(*, include_signals: bool) -> str:
    return f"sig={include_signals}"


def get_cached_credit_df(*, include_signals: bool) -> Any | None:
    return _CREDIT_DFS.get(credit_cache_key(include_signals=include_signals))


def set_cached_credit_df(*, include_signals: bool, df: Any) -> None:
    _CREDIT_DFS[credit_cache_key(include_signals=include_signals)] = df


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
