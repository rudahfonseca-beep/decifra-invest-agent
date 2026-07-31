#!/usr/bin/env python3
"""Rebuild docs/dashboard/index.html from AAR frontmatter, improvements, and prompts."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
AAR_DIR = DOCS / "aar"
AUTO_DIR = AAR_DIR / "automation"
IMPROVEMENTS = DOCS / "improvements" / "LOG.md"
PROMPTS = DOCS / "prompts" / "FUTURE_AGENTS.md"
OUT_HTML = DOCS / "dashboard" / "index.html"
CSS_HREF = "assets/dashboard.css"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LESSONS_RE = re.compile(
    r"^## 4\. Lessons\s*\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def parse_frontmatter(text: str) -> dict[str, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip().strip('"').split("#")[0].strip()
    return meta


def load_aars() -> list[dict]:
    files = sorted(AAR_DIR.glob("*.md")) + sorted(AUTO_DIR.glob("*.md"))
    items: list[dict] = []
    for path in files:
        if path.name.startswith("_") or path.name.upper() == "INDEX.MD":
            continue
        if path.name == ".gitkeep":
            continue
        text = path.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if not meta.get("id"):
            meta["id"] = path.stem
        meta["path"] = path
        rel = path.relative_to(DOCS).as_posix()
        meta["href"] = f"../{rel}"
        meta["lessons_excerpt"] = ""
        lm = LESSONS_RE.search(text)
        if lm:
            bullets = [
                ln.strip("- ").strip()
                for ln in lm.group(1).splitlines()
                if ln.strip().startswith("-")
            ]
            meta["lessons_excerpt"] = bullets[:3]
        items.append(meta)
    items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return items


def parse_improvements_open(text: str) -> list[dict[str, str]]:
    """Parse the Open table from improvements LOG."""
    if "## Open" not in text:
        return []
    section = text.split("## Open", 1)[1]
    if "## Done" in section:
        section = section.split("## Done", 1)[0]
    rows: list[dict[str, str]] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 5 or cols[0] in ("ID", "----") or set(cols[0]) <= {"-"}:
            continue
        rows.append(
            {
                "id": cols[0],
                "date": cols[1] if len(cols) > 1 else "",
                "source": cols[2] if len(cols) > 2 else "",
                "improvement": cols[3] if len(cols) > 3 else "",
                "priority": cols[4] if len(cols) > 4 else "",
                "notes": cols[5] if len(cols) > 5 else "",
            }
        )
    return rows


def parse_prompts(text: str) -> list[dict[str, str]]:
    """Extract numbered prompts: **Title** then body until blank or next number."""
    prompts: list[dict[str, str]] = []
    # Match: 1. **Title** then following lines until next N. ** or EOF
    pattern = re.compile(
        r"^(\d+)\.\s+\*\*(.+?)\*\*\s*\n(.*?)(?=^\d+\.\s+\*\*|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for m in pattern.finditer(text):
        body = m.group(3).strip()
        # Prefer fenced or backtick-wrapped single line; else strip backticks
        body = body.strip("`").strip()
        prompts.append({"n": m.group(1), "title": m.group(2).strip(), "body": body})
    return prompts


def summarize_coverage(aars: list[dict]) -> dict[str, str]:
    """Pull coverage numbers from the newest automation AAR if present."""
    for a in aars:
        if a.get("session_type") == "automation":
            path: Path = a["path"]
            text = path.read_text(encoding="utf-8")
            # Look for simple key: value lines under coverage
            cov: dict[str, str] = {}
            for key in ("tickers", "financials", "prices", "notices", "transcripts"):
                m = re.search(rf"(?i){key}\s*[:=]\s*([^\n|]+)", text)
                if m:
                    cov[key] = m.group(1).strip()
            if cov:
                return cov
    return {}


def render_html(
    aars: list[dict],
    improvements: list[dict[str, str]],
    prompts: list[dict[str, str]],
    coverage: dict[str, str],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    agent_n = sum(1 for a in aars if a.get("session_type") == "agent")
    auto_n = sum(1 for a in aars if a.get("session_type") == "automation")

    cards = []
    for a in aars:
        st = a.get("status", "unknown")
        stype = a.get("session_type", "agent")
        cards.append(
            f"""
      <article class="card">
        <div class="meta-row">
          <span class="badge badge-{escape(stype)}">{escape(stype)}</span>
          <span class="badge badge-{escape(st)}">{escape(st)}</span>
          {escape(a.get("date", ""))}
        </div>
        <h3><a href="{escape(a.get("href", "#"))}">{escape(a.get("title", a.get("id", "")))}</a></h3>
        <div class="meta-row">{escape(a.get("id", ""))}</div>
      </article>"""
        )

    lesson_items: list[str] = []
    for a in aars:
        for bullet in a.get("lessons_excerpt") or []:
            lesson_items.append(
                f"<li><strong>{escape(a.get('title', ''))}:</strong> {escape(bullet)}</li>"
            )
        if len(lesson_items) >= 12:
            break

    imp_rows = []
    for row in improvements:
        pri = row.get("priority", "").lower()
        pri_class = (
            "priority-high"
            if "high" in pri
            else "priority-med"
            if "med" in pri
            else "priority-low"
        )
        imp_rows.append(
            f"""<tr>
          <td>{escape(row['id'])}</td>
          <td>{escape(row.get('improvement', ''))}</td>
          <td class="{pri_class}">{escape(row.get('priority', ''))}</td>
          <td>{escape(row.get('source', ''))}</td>
        </tr>"""
        )

    prompt_lis = []
    for p in prompts:
        prompt_lis.append(
            f"""<li>
          <strong>{escape(p['n'])}. {escape(p['title'])}</strong>
          <div class="prompt-body">{escape(p['body'])}</div>
        </li>"""
        )

    cov_stats = ""
    if coverage:
        for k, v in coverage.items():
            cov_stats += f"""
      <div class="stat"><div class="label">{escape(k)}</div><div class="value">{escape(v)}</div></div>"""
    else:
        cov_stats = '<p class="empty">No automation coverage snapshot yet. Run <code>scripts/sync_pilot.py</code>.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>decifra-invest-agent — Session dashboard</title>
  <link rel="stylesheet" href="{CSS_HREF}" />
</head>
<body>
  <div class="wrap">
    <header>
      <h1>decifra-invest-agent session dashboard</h1>
      <p class="sub">Human view of agent AARs, automation traces, improvements, and future prompts.</p>
      <p class="meta">Generated {escape(now)} · {agent_n} agent · {auto_n} automation AARs</p>
    </header>

    <section>
      <h2>Coverage snapshot</h2>
      <div class="stats">{cov_stats}
      </div>
    </section>

    <section>
      <h2>Session timeline</h2>
      <div class="grid">
        {"".join(cards) if cards else '<p class="empty">No AARs yet.</p>'}
      </div>
    </section>

    <section>
      <h2>Open improvements</h2>
      {"<table><thead><tr><th>ID</th><th>Improvement</th><th>Priority</th><th>Source</th></tr></thead><tbody>" + "".join(imp_rows) + "</tbody></table>" if imp_rows else '<p class="empty">No open improvements.</p>'}
    </section>

    <section>
      <h2>Lessons rollup</h2>
      <div class="lessons">
        {"<ul>" + "".join(lesson_items) + "</ul>" if lesson_items else '<p class="empty">No lessons extracted yet.</p>'}
      </div>
    </section>

    <section>
      <h2>Prompts for future agents</h2>
      <ul class="prompt-list">
        {"".join(prompt_lis) if prompt_lis else '<p class="empty">No prompts seeded.</p>'}
      </ul>
    </section>

    <footer>
      Agent sources: <code>docs/aar/</code> · Improvements: <code>docs/improvements/LOG.md</code> ·
      Update: <code>python scripts/update_session_dashboard.py</code>
    </footer>
  </div>
</body>
</html>
"""


def main() -> int:
    aars = load_aars()
    improvements = parse_improvements_open(
        IMPROVEMENTS.read_text(encoding="utf-8") if IMPROVEMENTS.exists() else ""
    )
    prompts = parse_prompts(PROMPTS.read_text(encoding="utf-8") if PROMPTS.exists() else "")
    coverage = summarize_coverage(aars)
    html = render_html(aars, improvements, prompts, coverage)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT_HTML} ({len(aars)} AARs, {len(improvements)} open improvements, {len(prompts)} prompts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
