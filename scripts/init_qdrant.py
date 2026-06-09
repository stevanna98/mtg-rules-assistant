"""Initialize the Qdrant `rules` collection. Idempotent — safe to re-run."""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from mtg_rules.config import settings
from mtg_rules.embeddings import VECTOR_SIZE


COLLECTION_NAME = "rules"


def main() -> None:
    client = QdrantClient(url=settings.qdrant_url)

    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME in existing:
        print(f"Collection {COLLECTION_NAME!r} already exists. Skipping.")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Created collection {COLLECTION_NAME!r} (size={VECTOR_SIZE}, cosine).")


if __name__ == "__main__":
    main()
