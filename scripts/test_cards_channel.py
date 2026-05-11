import asyncio
from mtg_rules.retrieval.cards import cards_channel


QUESTIONS = [
    "Can I cast Lightning Bolt while Leyline of Sanctity is on the battlefield?",
    "Does Force of Will counter Counterspell?",
    "If a creature has hexproof, can it still be destroyed?",  # no cards expected
]


async def main() -> None:
    for q in QUESTIONS:
        print(f"\nQ: {q}")
        cards = await cards_channel(q)
        if not cards:
            print("  → no cards extracted")
            continue
        for c in cards:
            text = c.get("oracle_text", "")[:80].replace("\n", " ")
            print(f"  {c['name']} — {text}")


if __name__ == "__main__":
    asyncio.run(main())
