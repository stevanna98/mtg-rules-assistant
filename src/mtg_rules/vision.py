"""Vision channel: identify MTG cards in an uploaded image using Groq vision."""

import base64

from groq import AsyncGroq

from mtg_rules.config import settings

_client: AsyncGroq | None = None

_IDENTIFY_PROMPT = (
    "List every Magic: The Gathering card name visible in this image. "
    "Return only the card names, one per line, with no extra text. "
    "If no MTG cards are visible, return an empty response."
)


def _get_groq() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def identify_cards_from_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> list[str]:
    """Return MTG card names identified in the image, or empty list on failure."""
    b64 = base64.b64encode(image_bytes).decode()
    data_url = f"data:{mime_type};base64,{b64}"
    try:
        response = await _get_groq().chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": data_url}},
                        {"type": "text", "text": _IDENTIFY_PROMPT},
                    ],
                }
            ],
        )
        raw = response.choices[0].message.content or ""
        return [line.strip() for line in raw.splitlines() if line.strip()]
    except Exception as e:
        print(f"[vision] identify_cards_from_image failed: {e}")
        return []
