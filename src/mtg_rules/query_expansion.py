"""Query expansion via multi-aspect HyDE (Hypothetical Document Embeddings).

Asks Groq (free tier) to write several short hypothetical rules passages, each
covering a DIFFERENT rules concept implicated by the question. Embedding those
passages alongside the raw question bridges the register gap between casual
English and MTG rules legalese, and covers questions that hinge on more than
one rules area (e.g. targeting legality + stack order + state-based actions).
"""

import json
import re

from groq import Groq
from mtg_rules.config import settings


_client: Groq | None = None

_SYSTEM = (
    "You are an expert MTG judge. Given a question about Magic: The Gathering rules, "
    "first identify which Comprehensive Rules concept DECIDES the answer, then any "
    "secondary concepts involved (e.g. targeting legality, the stack and resolution "
    "order, mana abilities, priority, state-based actions, layers, combat damage).\n\n"
    "Write 2-3 concise passages (1-2 sentences each) in the prose style of the MTG "
    "Comprehensive Rules, each covering a DIFFERENT one of those concepts. The FIRST "
    "passage must state the rule that most directly decides the question. Use precise "
    "MTG terminology (e.g. 'mana ability', 'the stack', 'state-based actions', "
    "'priority', 'resolves'). Do NOT include rule numbers or citations — prose only. "
    "Do NOT answer conversationally.\n\n"
    'Respond with JSON only, in exactly this shape: {"passages": ["...", "...", "..."]}'
)

# HyDE models sometimes prepend invented rule numbers ("614.7 If a spell...")
# despite instructions. Those fake citations poison BM25 (docs are indexed with
# their real rule numbers), so strip anything that looks like one.
_RULE_NUM = re.compile(r"\b\d{3}(\.\d+[a-z]?)?\.?\s*")


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def expand_query(question: str) -> list[str]:
    """Return hypothetical rules passages for the question, or [] on failure."""
    try:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=400,
            temperature=0,
            seed=42,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": question},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        passages = data.get("passages", [])
        cleaned = [_RULE_NUM.sub("", p).strip() for p in passages if isinstance(p, str)]
        return [p for p in cleaned if p][:3]
    except Exception:
        return []
