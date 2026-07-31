from __future__ import annotations

import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from decifra.config import DOWNLOAD_SLEEP_S, HTTP_TIMEOUT, USER_AGENT


def client() -> httpx.Client:
    return httpx.Client(
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        follow_redirects=True,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=20))
def download_bytes(url: str, *, params: dict | None = None) -> bytes:
    with client() as c:
        resp = c.get(url, params=params)
        resp.raise_for_status()
        return resp.content


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=20))
def download_json(url: str, *, params: dict | None = None) -> dict | list:
    with client() as c:
        resp = c.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def download_to_file(url: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    data = download_bytes(url)
    dest.write_bytes(data)
    time.sleep(DOWNLOAD_SLEEP_S)
    return dest


def normalize_cnpj(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit()).zfill(14)


def normalize_ticker(ticker: str) -> str:
    return ticker.strip().upper().replace(".SA", "")
