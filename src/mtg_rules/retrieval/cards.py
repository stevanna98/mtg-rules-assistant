"""Cards retrieval channel.

Given a rules question, extract any MTG card names mentioned, then fetch each
card's data from Scryfall in parallel.
"""
import asyncio
from groq import AsyncGroq
from mtg_rules.config import settings
from mtg_rules.scryfall import get_card


_client: AsyncGroq | None = None


def _get_groq() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


EXTRACT_CARDS_TOOL = {
    "type": "function",
    "function": {
        "name": "register_cards",
        "description": "Register the names of MTG cards mentioned in the question.",
        "parameters": {
            "type": "object",
            "properties": {
                "card_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Exact card names as written in the question. Empty list if no "
                        "specific cards are mentioned. Do NOT include card types "
                        "(creature, instant) or generic terms (a creature, my creatures)."
                    ),
                }
            },
            "required": ["card_names"],
        },
    },
}

EXTRACT_PROMPT = """Extract the names of all Magic: The Gathering cards mentioned in this question.

Rules:
- Return only literal card names as written in the question.
- Do NOT include card types (e.g. "creature", "instant", "land") — only specific named cards.
- Do NOT include generic phrases like "a creature" or "my creature".
- If no specific cards are mentioned, return an empty list.
- Card names may use shorthand (e.g. "Bolt" for "Lightning Bolt"). If unambiguous, expand them.

Question: {question}"""


async def extract_card_names(question: str) -> list[str]:
    """Use Groq (Llama 3.3 70B) to extract card names from a rules question."""
    import json

    response = await _get_groq().chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=512,
        tools=[EXTRACT_CARDS_TOOL],
        tool_choice={"type": "function", "function": {"name": "register_cards"}},
        messages=[
            {"role": "user", "content": EXTRACT_PROMPT.format(question=question)}
        ],
    )
    msg = response.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            if tc.function.name == "register_cards":
                data = json.loads(tc.function.arguments)
                names = data.get("card_names", [])
                return [n for n in names if isinstance(n, str) and n.strip()]
    return []


async def cards_channel(question: str) -> list[dict]:
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

    cards: list[dict] = []
    for name, r in zip(names, results):
        if isinstance(r, Exception):
            print(f"[cards_channel] Could not resolve {name!r}: {r}")
            continue
        cards.append(r)
    return cards
