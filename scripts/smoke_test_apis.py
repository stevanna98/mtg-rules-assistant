"""Smoke test the embeddings and Groq API."""

import asyncio
from groq import AsyncGroq
from mtg_rules.config import settings
from mtg_rules.embeddings import embed_text, VECTOR_SIZE


async def main() -> None:
    # Local embeddings
    vec = embed_text("hello world")
    assert len(vec) == VECTOR_SIZE, f"Expected {VECTOR_SIZE} dims, got {len(vec)}"
    print(f"Embeddings OK: {len(vec)}-dim vector for 'hello world'")

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
