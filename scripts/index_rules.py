"""Chunk parsed rules, embed them, and upsert into Qdrant.

Idempotent — re-running re-indexes from scratch. Run this whenever the rules update.
"""
import json
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from mtg_rules.config import settings
from mtg_rules.chunking import build_chunk_text
from mtg_rules.embeddings import embed_documents, VECTOR_SIZE


COLLECTION_NAME = "rules"
RULES_PATH = Path("data/processed/rules.jsonl")


def main() -> None:
    rules: list[dict] = []
    with RULES_PATH.open() as f:
        for line in f:
            rules.append(json.loads(line))
    print(f"Loaded {len(rules)} rules from {RULES_PATH}")

    by_number = {r["rule_number"]: r for r in rules}

    chunk_texts: list[str] = []
    for r in rules:
        parent = by_number.get(r.get("parent_number") or "")
        chunk_texts.append(build_chunk_text(r, parent))

    sample_idx = next(
        (i for i, r in enumerate(rules) if r["rule_number"] == "702.10a"),
        0,
    )
    print("\n--- Sample chunk ---")
    print(chunk_texts[sample_idx])
    print("--- End sample ---\n")

    print(f"Embedding {len(chunk_texts)} chunks...")
    vectors = embed_documents(chunk_texts, batch_size=256)
    assert len(vectors) == len(chunk_texts)
    assert len(vectors[0]) == VECTOR_SIZE, f"Expected {VECTOR_SIZE} dims, got {len(vectors[0])}"

    client = QdrantClient(url=settings.qdrant_url)

    points = [
        PointStruct(
            id=i,
            vector=vec,
            payload={
                "rule_number": r["rule_number"],
                "parent_number": r.get("parent_number"),
                "section": r.get("section", ""),
                "depth": r.get("depth", 0),
                "text": chunk_text,
                "raw_text": r["text"],
                "examples": r.get("examples", []),
            },
        )
        for i, (r, chunk_text, vec) in enumerate(zip(rules, chunk_texts, vectors))
    ]

    print(f"Upserting {len(points)} points...")
    client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)

    info = client.get_collection(COLLECTION_NAME)
    print(f"Collection now has {info.points_count} points.")


if __name__ == "__main__":
    main()
