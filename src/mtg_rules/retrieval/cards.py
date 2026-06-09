"""Cards retrieval channel.

Given a rules question, extract any MTG card names mentioned, then fetch each
card's data from Scryfall in parallel.
"""

import asyncio
import json
from groq import AsyncGroq
from mtg_rules.config import settings
from mtg_rules.scryfall import get_card


_client: AsyncGroq | None = None


def _get_groq() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


EXTRACT_PROMPT = """Extract the names of all Magic: The Gathering cards mentioned in this question.

Rules:
- Return only literal card names as written in the question.
- Do NOT include card types (e.g. "creature", "instant", "land") — only specific named cards.
- Do NOT include generic phrases like "a creature" or "my creature".
- If no specific cards are mentioned, return an empty list.
- Card names may use shorthand (e.g. "Bolt" for "Lightning Bolt"). If unambiguous, expand them.

Respond with JSON only, in exactly this shape: {{"card_names": ["...", "..."]}}

Question: {question}"""


async def extract_card_names(question: str) -> list[str]:
    """Use Groq (Llama 3.3 70B) to extract card names from a rules question.

    Returns an empty list on any extraction failure — a missing cards channel
    degrades the answer, but must never take down the whole request.
    """
    try:
        response = await _get_groq().chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=512,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": EXTRACT_PROMPT.format(question=question)}],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        names = data.get("card_names", [])
        return [n for n in names if isinstance(n, str) and n.strip()]
    except Exception as e:
        print(f"[cards_channel] card name extraction failed: {e}")
        return []


async def cards_channel(question: str) -> list[dict]:  # type: ignore[type-arg]
    """Extract card names from a question and fetch their Scryfall data in parallel.

    Cards that can't be found on Scryfall are silently dropped.
    """
    names = await extract_card_names(question)
    if not names:
        return []

    results = await asyncio.gather(
        *[get_card(name) for name in names],
        return_exceptions=True,
    )

    cards: list[dict] = []  # type: ignore[type-arg]
    for name, r in zip(names, results):
        if isinstance(r, Exception):
            print(f"[cards_channel] Could not resolve {name!r}: {r}")
            continue
        assert isinstance(r, dict)
        cards.append(r)
    return cards
