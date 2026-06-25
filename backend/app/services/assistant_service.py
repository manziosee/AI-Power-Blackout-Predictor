"""LLM assistant with RAG context from DB outages and predictions."""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.1-8b-instant"
_MAX_CONTEXT_ROWS = 5


async def _build_context(db: AsyncSession, h3_index: str | None) -> str:
    """Query recent outages + predictions and format as RAG context."""
    ctx_lines: list[str] = []

    try:
        if h3_index:
            rows = await db.execute(
                text(
                    "SELECT verified, created_at FROM outage_reports "
                    "WHERE h3_index = :h3 ORDER BY created_at DESC LIMIT :n"
                ),
                {"h3": h3_index, "n": _MAX_CONTEXT_ROWS},
            )
            for r in rows.fetchall():
                ctx_lines.append(f"- Outage at {h3_index}: verified={r[0]}, at {r[1]}")

            rows = await db.execute(
                text(
                    "SELECT probability, risk_level, window_start FROM predictions "
                    "WHERE h3_index = :h3 ORDER BY created_at DESC LIMIT :n"
                ),
                {"h3": h3_index, "n": _MAX_CONTEXT_ROWS},
            )
            for r in rows.fetchall():
                ctx_lines.append(
                    f"- Prediction: probability={r[0]:.0%}, risk={r[1]}, window={r[2]}"
                )
        else:
            rows = await db.execute(
                text(
                    "SELECT h3_index, COUNT(*) as cnt FROM outage_reports "
                    "WHERE created_at > NOW() - INTERVAL '7 days' "
                    "GROUP BY h3_index ORDER BY cnt DESC LIMIT :n"
                ),
                {"n": _MAX_CONTEXT_ROWS},
            )
            for r in rows.fetchall():
                ctx_lines.append(f"- Top outage cell {r[0]}: {r[1]} reports in 7 days")
    except Exception as exc:
        logger.debug("RAG context query failed: %s", exc)

    if not ctx_lines:
        return "No recent outage data available."
    return "\n".join(ctx_lines)


async def ask(
    question: str,
    db: AsyncSession,
    h3_index: str | None = None,
    language: str = "en",
) -> str:
    """Answer a question about power outages using RAG context from the DB."""
    if not settings.GROQ_API_KEY:
        return "LLM assistant is not configured (GROQ_API_KEY missing)."

    context = await _build_context(db, h3_index)
    system_prompt = (
        "You are an AI assistant for a power outage prediction platform. "
        "Answer questions factually and concisely based on the provided context. "
        "If the context does not contain enough information, say so. "
        "Reply in the same language as the user's question."
    )
    user_msg = f"Context:\n{context}\n\nQuestion: {question}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _GROQ_URL,
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": _MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 300,
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.warning("Assistant ask() failed: %s", exc)
        return "I'm unable to answer right now. Please try again later."
