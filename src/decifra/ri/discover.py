from __future__ import annotations

from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from decifra.config import USER_AGENT
from decifra.http_util import client
from decifra.store.folders import load_meta, save_meta


CALL_KEYWORDS = (
    "teleconferencia",
    "teleconferência",
    "transcript",
    "transcricao",
    "transcrição",
    "earnings call",
    "audio",
    "áudio",
    "apresentacao",
    "apresentação",
    "webcast",
    "call de resultados",
    "resultado",
)


def get_ri_url(ticker: str) -> str:
    meta = load_meta(ticker)
    url = (meta.get("ri_url") or "").strip()
    if url and not url.startswith("http"):
        url = "https://" + url
    return url


def harvest_ri_document_links(ri_url: str, *, max_pages: int = 1, max_links: int = 40) -> list[dict]:
    """Best-effort crawl of an RI homepage for call/presentation PDFs."""
    if not ri_url:
        return []
    found: list[dict] = []
    seen: set[str] = set()
    try:
        with client() as c:
            resp = c.get(ri_url)
            resp.raise_for_status()
            html = resp.text
    except (httpx.HTTPError, ValueError):
        return []

    soup = BeautifulSoup(html, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = " ".join(a.get_text(" ", strip=True).split())
        abs_url = urljoin(ri_url, href)
        if abs_url in seen:
            continue
        blob = f"{text} {abs_url}".lower()
        if not any(k in blob for k in CALL_KEYWORDS):
            continue
        path = urlparse(abs_url).path.lower()
        if not (path.endswith(".pdf") or "pdf" in blob or "audio" in blob or "transcript" in blob):
            # Keep HTML pages that look like call pages too
            if not any(k in blob for k in ("teleconfer", "transcript", "webcast", "apresenta")):
                continue
        seen.add(abs_url)
        found.append({"title": text or abs_url, "url": abs_url, "source": "ri_site"})
        if len(found) >= max_links:
            break
    return found


def refresh_ri_url_from_meta(ticker: str, ri_url: str) -> None:
    if not ri_url:
        return
    meta = load_meta(ticker)
    meta["ri_url"] = ri_url
    save_meta(ticker, meta)
