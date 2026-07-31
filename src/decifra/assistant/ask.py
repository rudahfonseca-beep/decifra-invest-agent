from __future__ import annotations

from typing import Any

from decifra.assistant.llm import chat_completion
from decifra.assistant.retrieve import (
    extract_ticker,
    extract_year,
    search_financials,
    search_notices,
    search_transcripts,
)
from decifra.config import OPENAI_API_KEY


def _detect_intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ("fato", "comunicado", "aviso", "notice", "relevanter")):
        return "notices"
    if any(w in q for w in ("transcri", "teleconfer", "call", "apresenta", "webcast")):
        return "transcripts"
    if any(w in q for w in ("receita", "lucro", "ebitda", "balanço", "balanco", "dre", "caixa", "financeiro", "ativo")):
        return "financials"
    return "auto"


def _optional_llm_summarize(question: str, context: str) -> str | None:
    if not OPENAI_API_KEY or not context.strip():
        return None
    return chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "Você é um assistente de research do mercado brasileiro. "
                    "Responda com base apenas no contexto fornecido. "
                    "Se faltar dado, diga o que falta. Responda em português."
                ),
            },
            {
                "role": "user",
                "content": f"Pergunta: {question}\n\nContexto:\n{context[:12000]}",
            },
        ],
        temperature=0.2,
        timeout=60.0,
    )


def answer_question(question: str) -> dict[str, Any]:
    ticker = extract_ticker(question)
    year = extract_year(question)
    intent = _detect_intent(question)

    if not ticker:
        return {
            "ok": False,
            "error": "Não identifiquei um ticker Ibovespa na pergunta. Ex.: PETR4, VALE3.",
            "question": question,
        }

    sections: list[str] = []
    payload: dict[str, Any] = {
        "ok": True,
        "ticker": ticker,
        "year": year,
        "intent": intent,
        "question": question,
    }

    run_fin = intent in {"financials", "auto"}
    run_notices = intent in {"notices", "auto"}
    run_calls = intent in {"transcripts", "auto"}

    if run_fin:
        fin = search_financials(ticker, question, year=year)
        payload["financials"] = fin.to_dict(orient="records") if not fin.empty else []
        if not fin.empty:
            sections.append("FINANCEIRO\n" + fin.to_string(index=False))

    if run_notices:
        notices = search_notices(ticker, query=None if intent == "auto" else question, year=year)
        # For auto, if question mentions notices keywords already filtered by intent
        if intent == "notices":
            notices = search_notices(ticker, year=year, limit=30)
        payload["notices"] = notices.to_dict(orient="records") if not notices.empty else []
        if not notices.empty:
            cols = [c for c in ["date", "category", "title", "local_path"] if c in notices.columns]
            sections.append("NOTICES\n" + notices[cols].head(15).to_string(index=False))

    if run_calls:
        calls = search_transcripts(ticker, query=None, limit=15)
        payload["transcripts"] = calls
        if calls:
            lines = [f"- {c.get('date','')} | {c.get('title','')[:80]} | {c.get('local_path','')}" for c in calls[:12]]
            sections.append("TRANSCRIPTS/CALLS\n" + "\n".join(lines))

    context = "\n\n".join(sections)
    summary = _optional_llm_summarize(question, context)
    if summary:
        payload["answer"] = summary
    else:
        if not sections:
            payload["answer"] = (
                f"Sem dados locais para {ticker}. Rode: "
                f"`decifra sync financials --ticker {ticker}` e "
                f"`decifra sync notices --ticker {ticker}`."
            )
        else:
            payload["answer"] = context

    return payload
