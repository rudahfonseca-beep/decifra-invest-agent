#!/usr/bin/env python3
"""Pilot automation: run decifra-invest-agent sync stages, capture coverage delta, write AAR."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Core lake stages (default). Pipeline phases 1+ add fre/anbima/b3-* when opted in.
CORE_STAGES = ("universe", "financials", "notices", "transcripts")
PIPELINE_STAGES = ("fre", "anbima", "b3-shares", "b3-bonds", "funds", "edgar")
ALL_STAGES = CORE_STAGES + PIPELINE_STAGES


def _python() -> str:
    """Prefer project venv interpreter when available."""
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    unix = ROOT / ".venv" / "bin" / "python"
    if win.exists():
        return str(win)
    if unix.exists():
        return str(unix)
    return sys.executable


def summarize_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {
            "tickers": 0,
            "financials": "0/0",
            "prices": "0/0",
            "notices": "0/0",
            "transcripts": "0/0",
            "missing_financials": [],
            "missing_prices_count": 0,
        }

    def has_fin(r: dict[str, Any]) -> bool:
        return bool(r.get("income_statement") and r.get("balance_sheet") and r.get("cash_flow"))

    fin_ok = sum(1 for r in rows if has_fin(r))
    prices_ok = sum(1 for r in rows if r.get("prices"))
    notices_ok = sum(1 for r in rows if r.get("notices"))
    tx_ok = sum(1 for r in rows if r.get("transcripts"))
    missing_fin = [r["ticker"] for r in rows if not has_fin(r)]
    return {
        "tickers": n,
        "financials": f"{fin_ok}/{n}",
        "prices": f"{prices_ok}/{n}",
        "notices": f"{notices_ok}/{n}",
        "transcripts": f"{tx_ok}/{n}",
        "missing_financials": missing_fin,
        "missing_prices_count": n - prices_ok,
        "notice_pdfs": sum(int(r.get("notice_pdfs") or 0) for r in rows),
        "transcript_files": sum(int(r.get("transcript_files") or 0) for r in rows),
    }


def capture_coverage() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from decifra.assistant.retrieve import coverage_status

    rows = coverage_status()
    return rows, summarize_coverage(rows)


def run_stage(stage: str, dry_run: bool, ticker: str | None) -> dict[str, Any]:
    """Run one sync stage via `python -m decifra`."""
    py = _python()
    cmd = [py, "-m", "decifra", "sync", stage]
    if ticker and stage != "universe":
        cmd.extend(["--ticker", ticker])
    if dry_run:
        return {"stage": stage, "cmd": cmd, "dry_run": True, "ok": True, "returncode": 0}
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "stage": stage,
        "cmd": cmd,
        "dry_run": False,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-2000:],
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


def write_aar(
    *,
    stages: list[str],
    before: dict[str, Any],
    after: dict[str, Any],
    results: list[dict[str, Any]],
    dry_run: bool,
    ticker: str | None,
) -> Path:
    today = date.today().isoformat()
    slug = f"{today}-sync-pilot"
    if dry_run:
        slug += "-dry-run"
    out_dir = ROOT / "docs" / "aar" / "automation"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slug}.md"

    failed = [r for r in results if not r.get("ok")]
    status = "completed" if not failed else "completed"  # still emit AAR
    if dry_run:
        status = "completed"

    def fmt(cov: dict[str, Any]) -> str:
        return (
            f"- tickers: {cov.get('tickers')}\n"
            f"- financials: {cov.get('financials')}\n"
            f"- prices: {cov.get('prices')}\n"
            f"- notices: {cov.get('notices')}\n"
            f"- transcripts: {cov.get('transcripts')}\n"
            f"- notice_pdfs: {cov.get('notice_pdfs', 'n/a')}\n"
            f"- transcript_files: {cov.get('transcript_files', 'n/a')}\n"
            f"- missing_financials: {', '.join(cov.get('missing_financials') or []) or '(none)'}\n"
            f"- missing_prices_count: {cov.get('missing_prices_count')}\n"
        )

    stage_lines = []
    for r in results:
        mark = "OK" if r.get("ok") else f"FAIL({r.get('returncode')})"
        cmd_s = " ".join(str(x) for x in r.get("cmd", []))
        stage_lines.append(f"- `{r['stage']}`: {mark} — `{cmd_s}`")
        if r.get("stderr_tail") and not r.get("ok"):
            stage_lines.append(f"  - stderr: ```\n{r['stderr_tail'][:800]}\n```")

    gaps = []
    if dry_run:
        gaps.append("Dry-run only — no network sync executed.")
    if after.get("missing_financials"):
        gaps.append(
            f"Missing full financial CSVs: {', '.join(after['missing_financials'])} "
            "(known CVM gap / IMP-002)."
        )
    if after.get("missing_prices_count"):
        gaps.append(
            f"{after['missing_prices_count']} tickers still missing prices.csv "
            "(see IMP-001 if unexpected)."
        )
    if failed:
        gaps.append(f"Failed stages: {', '.join(r['stage'] for r in failed)}.")
    if not gaps:
        gaps.append("No new gaps detected beyond baseline lake health.")

    auto_rows = _automation_opportunity_rows(
        dry_run=dry_run,
        failed=failed,
        after=after,
    )

    body = f"""---
id: {slug}
date: {today}
title: Sync pilot{" (dry-run)" if dry_run else ""}
session_type: automation
transcript_id: ""
status: {status}
---

# AAR: Sync pilot{" (dry-run)" if dry_run else ""}

## 1. Plan / purpose / objective

Automate existing decifra-invest-agent data collection (`decifra sync`) for stages: **{", ".join(stages)}**.
Capture before/after coverage, write this automation AAR, and **refresh the human HTML dashboard** (required closeout).
{"Ticker filter: " + ticker if ticker else "Universe: full Ibovespa set."}
Dry-run: **{dry_run}**.

## 2. What actually happened

Ran `scripts/sync_pilot.py` at {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}.

### Stages

{chr(10).join(stage_lines)}

### Coverage before

{fmt(before)}

### Coverage after

{fmt(after)}

### Machine-readable summary

```json
{json.dumps({"before": before, "after": after, "stages": stages, "dry_run": dry_run}, indent=2, ensure_ascii=False)}
```

## 3. Gaps

{chr(10).join("- " + g for g in gaps)}

## 4. Lessons

- Idempotent CVM ZIP cache makes re-sync safe; status delta is the audit trail.
- Prefer `scripts/sync_pilot.py` over ad-hoc sync so every collection run leaves an AAR **and** refreshes the dashboard.
- Transcripts/RI crawl is the slowest stage — use `--skip-transcripts` for refresh loops.
- Product/data gaps: [`docs/improvements/LOG.md`](../../improvements/LOG.md). Automation meta: [`docs/improvements/AUTOMATION.md`](../../improvements/AUTOMATION.md).

## 5. Improvements

### Product / data

See open `IMP-*` rows in [`docs/improvements/LOG.md`](../../improvements/LOG.md) (do not hardcode stale status here).

### Automation opportunities

| ID | Opportunity | Priority | Status |
|----|-------------|----------|--------|
{auto_rows}

Track lasting meta-follow-ups in [`docs/improvements/AUTOMATION.md`](../../improvements/AUTOMATION.md).
"""
    path.write_text(body, encoding="utf-8")
    return path


def _automation_opportunity_rows(
    *,
    dry_run: bool,
    failed: list[dict[str, Any]],
    after: dict[str, Any],
) -> str:
    """Rows for this run's AAR — standing open items + run-specific notes."""
    rows = [
        "| AUTO-001 | Cursor Automation wrapping this runner (IMP-008) | low | open |",
        "| AUTO-003 | Prefer sync_pilot over ad-hoc `decifra sync` | med | open |",
    ]
    if dry_run:
        rows.append(
            "| (run) | Dry-run — no lake mutation; dashboard still refreshed for AAR visibility | low | note |"
        )
    if failed:
        stages = ", ".join(r["stage"] for r in failed)
        rows.append(
            f"| (run) | Investigate failed stages: {stages} | high | open |"
        )
    if after.get("missing_prices_count"):
        rows.append(
            f"| (run) | Coverage: {after['missing_prices_count']} missing prices — confirm expected vs regression | med | note |"
        )
    return "\n".join(rows)


def update_index(aar_path: Path) -> None:
    index = ROOT / "docs" / "aar" / "INDEX.md"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")
    rel = aar_path.relative_to(ROOT / "docs" / "aar").as_posix()
    meta_id = aar_path.stem
    if meta_id in text:
        return
    today = date.today().isoformat()
    row = (
        f"| {today} | {meta_id} | Sync pilot | completed | "
        f"[{aar_path.name}]({rel}) |"
    )
    placeholder = "| _(populated by `scripts/sync_pilot.py`)_ | | | | |"
    if placeholder in text:
        text = text.replace(placeholder, row + "\n" + placeholder)
    else:
        marker = (
            "## Automation traces\n\n"
            "| Date | ID | Title | Status | File |\n"
            "|------|-----|-------|--------|------|\n"
        )
        if marker in text:
            text = text.replace(marker, marker + row + "\n")
    index.write_text(text, encoding="utf-8")


def refresh_dashboard() -> bool:
    """Rebuild human HTML dashboard. Required automation closeout; returns ok."""
    py = _python()
    script = ROOT / "scripts" / "update_session_dashboard.py"
    proc = subprocess.run(
        [py, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        print(
            f"ERROR: dashboard refresh failed (rc={proc.returncode})",
            file=sys.stderr,
        )
        if proc.stderr:
            print(proc.stderr[-1500:], file=sys.stderr)
        return False
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="decifra-invest-agent sync pilot with AAR output")
    p.add_argument(
        "--stages",
        default=",".join(CORE_STAGES),
        help=(
            f"Comma-separated stages (default: {','.join(CORE_STAGES)}). "
            f"Pipeline extras: {','.join(PIPELINE_STAGES)}"
        ),
    )
    p.add_argument("--skip-transcripts", action="store_true", help="Omit transcripts stage")
    p.add_argument("--ticker", default=None, help="Limit non-universe stages to one ticker")
    p.add_argument("--dry-run", action="store_true", help="Plan only; do not call network sync")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    for s in stages:
        if s not in ALL_STAGES:
            print(f"Unknown stage: {s}. Allowed: {ALL_STAGES}", file=sys.stderr)
            return 2
    if args.skip_transcripts:
        stages = [s for s in stages if s != "transcripts"]

    print(f"Interpreter: {_python()}")
    print(f"Stages: {stages} dry_run={args.dry_run} ticker={args.ticker}")

    before_rows, before = capture_coverage()
    print(f"Coverage before: {before}")

    results: list[dict[str, Any]] = []
    for stage in stages:
        print(f"Running stage: {stage}...")
        r = run_stage(stage, dry_run=args.dry_run, ticker=args.ticker)
        results.append(r)
        print(f"  -> {'OK' if r['ok'] else 'FAIL'} (rc={r.get('returncode')})")

    after_rows, after = capture_coverage()
    print(f"Coverage after: {after}")

    aar_path = write_aar(
        stages=stages,
        before=before,
        after=after,
        results=results,
        dry_run=args.dry_run,
        ticker=args.ticker,
    )
    print(f"Wrote AAR: {aar_path}")
    update_index(aar_path)
    dash_ok = refresh_dashboard()
    if dash_ok:
        print("Dashboard refreshed (required automation closeout).")
    else:
        print("Dashboard refresh failed — treating as automation failure.", file=sys.stderr)

    stages_ok = all(r.get("ok") for r in results)
    return 0 if stages_ok and dash_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
