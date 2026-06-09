"""Answer generation layer.

Takes the question plus retrieved rules and card context, builds a grounded
prompt, and calls Groq (gpt-oss-120b) to produce a rules-accurate answer.
"""

from groq import AsyncGroq
from mtg_rules.config import settings


_client: AsyncGroq | None = None

_SYSTEM = (
    "You are an expert Magic: The Gathering judge answering a player's question.\n"
    "\n"
    "The rules excerpts below were retrieved automatically by semantic search: "
    "some may be tangential or cover a similar-but-different case (e.g. a rule "
    "about triggered abilities when the question is about activated abilities). "
    "Rely only on the excerpts that genuinely apply, and silently ignore the rest "
    "— do not force your reasoning to fit an excerpt that doesn't match the "
    "question.\n"
    "\n"
    "Guidelines:\n"
    "- Start with a direct verdict (e.g. 'Yes,' / 'No,') before explaining.\n"
    "- Walk through the game logic step by step (stack order, resolution, "
    "state-based actions) when the question involves an interaction.\n"
    "- Cite a rule number inline (e.g. 'rule 605.3b') ONLY if that exact number "
    "appears in the excerpts below. Never cite a rule number from memory.\n"
    "- Use the card data as the authoritative text of the cards involved.\n"
    "- If the excerpts don't cover the deciding point, answer from your judge "
    "knowledge but say explicitly that the relevant rule was not retrieved.\n"
    "- Be concise: a verdict plus a short explanation, not an essay."
)


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


def _build_context(rules: list[dict], cards: list[dict]) -> str:  # type: ignore[type-arg]
    parts: list[str] = []

    if rules:
        parts.append("## Relevant Rules")
        for r in rules:
            line = f"Rule {r['rule_number']}: {r['raw_text']}"
            if r.get("examples"):
                line += " " + " ".join(r["examples"])
            parts.append(line)

    if cards:
        parts.append("\n## Relevant Cards")
        for c in cards:
            header = f"**{c['name']}** — {c.get('type_line', '')}"
            if c.get("mana_cost"):
                header += f" {c['mana_cost']}"
            parts.append(header)
            if c.get("oracle_text"):
                parts.append(c["oracle_text"])

    return "\n".join(parts)


async def generate_answer(
    question: str,
    rules: list[dict],  # type: ignore[type-arg]
    cards: list[dict],  # type: ignore[type-arg]
    history: list[dict] | None = None,  # type: ignore[type-arg]
) -> str:
    """Return a grounded natural-language answer for the question.

    history is a list of prior {"role": "user"|"assistant", "content": str} turns.
    Retrieved context is only injected for the current question, not replayed into history.
    """
    context = _build_context(rules, cards)
    user_content = f"{context}\n\n## Question\n{question}" if context else question

    messages: list[dict] = [{"role": "system", "content": _SYSTEM}]  # type: ignore[type-arg]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    try:
        # gpt-oss-120b is a reasoning model: it thinks before answering, which
        # matters for multi-step stack/state-based-action interactions where
        # llama-3.3-70b reliably tripped (e.g. believing a pump effect ends
        # when the spell finishes resolving). max_tokens must leave room for
        # the hidden reasoning tokens on top of the visible answer.
        response = await _get_client().chat.completions.create(
            model="openai/gpt-oss-120b",
            max_tokens=2048,
            temperature=0.2,
            messages=messages,  # type: ignore[arg-type]
        )
        return response.choices[0].message.content or "No answer generated."
    except Exception as e:
        return f"(answer generation failed: {e})"
