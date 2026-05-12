"""Spot-check retrieval quality with hand-written queries."""

from qdrant_client import QdrantClient
from mtg_rules.config import settings
from mtg_rules.embeddings import embed_text


COLLECTION_NAME = "rules"
QUERIES = [
    ("summoning sickness and haste", ["702.10"]),
    ("creature attacking", ["508"]),
    ("when does an instant resolve", ["608"]),
    ("hexproof targeting", ["702.11"]),
]


def main() -> None:
    client = QdrantClient(url=settings.qdrant_url)
    for q, expected_prefixes in QUERIES:
        vec = embed_text(q)
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vec,
            limit=5,
        )
        hits = results.points
        print(f"\nQuery: {q!r}")
        print(f"Expecting at least one rule starting with one of: {expected_prefixes}")
        for h in hits:
            rn = h.payload["rule_number"]
            print(f"  {h.score:.3f}  {rn}  {h.payload['raw_text'][:80]}")
        found = any(h.payload["rule_number"].startswith(p) for h in hits for p in expected_prefixes)
        print(f"  → {'FOUND' if found else 'MISSING'}")


if __name__ == "__main__":
    main()
