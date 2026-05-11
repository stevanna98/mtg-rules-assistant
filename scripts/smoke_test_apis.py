"""Smoke test the Voyage and Groq APIs. One call each, minimal cost."""
import asyncio
import voyageai
from groq import AsyncGroq
from mtg_rules.config import settings


async def main() -> None:
    # Voyage
    vo = voyageai.Client(api_key=settings.voyage_api_key)
    result = vo.embed(["hello world"], model="voyage-3-lite")
    embedding = result.embeddings[0]
    assert len(embedding) == 512, f"Expected 512 dims, got {len(embedding)}"
    print(f"Voyage OK: {len(embedding)}-dim embedding for 'hello world'")

    # Groq
    client = AsyncGroq(api_key=settings.groq_api_key)
    msg = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=32,
        messages=[{"role": "user", "content": "Say 'ok' and nothing else."}],
    )
    text = msg.choices[0].message.content
    print(f"Groq OK: response = {text!r}")


if __name__ == "__main__":
    asyncio.run(main())
