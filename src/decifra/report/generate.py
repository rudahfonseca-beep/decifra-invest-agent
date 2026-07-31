"""Write report artifacts (spec, context, prompt, optional HTML)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decifra.config import REPORTS_DIR, ensure_dirs
from decifra.report.assemble import assemble_context
from decifra.report.prompt import pack_messages, pack_prompt_markdown
from decifra.report.spec import ReportSpec


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return (s[:60] or "report")


def _strip_markdown_fence(html: str) -> str:
    text = html.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first fence and optional trailing fence
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def report_dir(slug: str) -> Path:
    ensure_dirs()
    path = REPORTS_DIR / slug
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_report_artifacts(
    spec: ReportSpec,
    *,
    generate: bool = False,
    out_dir: Path | None = None,
    credit_df: Any = None,
) -> dict[str, Any]:
    """
    Assemble context, always write spec/context/prompt; optionally call LLM for HTML.

    Returns paths and generation status.
    """
    context = assemble_context(spec, credit_df=credit_df)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"{_slugify(spec.default_title())}-{stamp}"
    dest = out_dir or report_dir(slug)
    dest.mkdir(parents=True, exist_ok=True)

    spec_path = dest / "spec.json"
    context_path = dest / "context.json"
    prompt_path = dest / "report.prompt.md"
    html_path = dest / "report.html"

    spec_path.write_text(
        json.dumps(spec.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    context_path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    prompt_md = pack_prompt_markdown(context)
    prompt_path.write_text(prompt_md, encoding="utf-8")

    result: dict[str, Any] = {
        "ok": True,
        "dir": str(dest),
        "slug": dest.name,
        "spec_path": str(spec_path),
        "context_path": str(context_path),
        "prompt_path": str(prompt_path),
        "html_path": None,
        "generated": False,
        "generate_error": None,
        "context": context,
        "prompt_markdown": prompt_md,
    }

    if generate:
        from decifra.assistant.llm import chat_completion
        from decifra.config import OPENAI_API_KEY

        if not OPENAI_API_KEY:
            result["generate_error"] = (
                "OPENAI_API_KEY not set — wrote prompt only. "
                "Paste report.prompt.md into an LLM or set the key and re-run with --generate."
            )
            return result

        messages = pack_messages(context)
        content = chat_completion(messages, temperature=0.2, timeout=180.0)
        if not content:
            result["generate_error"] = "LLM call failed or returned empty content"
            return result
        html = _strip_markdown_fence(content)
        html_path.write_text(html, encoding="utf-8")
        result["html_path"] = str(html_path)
        result["generated"] = True

    return result
