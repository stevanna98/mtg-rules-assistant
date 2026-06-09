"""Rules retrieval channel.

Hybrid three-stage pipeline:
  1. Query expansion (Groq multi-aspect HyDE) — generates 2-3 hypothetical
     rules passages, each covering a different rules concept implicated by the
     question, to bridge the register gap between casual English and MTG rules
     legalese.
  2. Multi-vector ANN retrieval — embeds the original question and each
     passage and fetches a candidate list from Qdrant per vector.
  3. Lexical retrieval — an in-memory BM25 index over all rules (built lazily
     from the Qdrant payloads; the corpus is only ~3.3k rules). The BM25 query
     is the question PLUS the HyDE passages, so the lexical search happens in
     Comprehensive Rules vocabulary ("activated mana ability", "responded to")
     rather than casual phrasing.

All candidate lists are fused with Reciprocal Rank Fusion (RRF). RRF is
scale-free, so dense lists and the BM25 list contribute equally even though
their score distributions are incomparable.

A cross-encoder reranker (ms-marco-MiniLM-L-6-v2) was evaluated but removed:
it has no MTG-specific training and actively demoted correct rules by ranking
surface-level keyword matches above semantically relevant ones.
"""

import os
import re

from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]

from mtg_rules.config import settings
from mtg_rules.embeddings import embed_text
from mtg_rules.query_expansion import expand_query


COLLECTION_NAME = "rules"
# Candidates fetched per candidate list. RRF rewards rules that rank well in
# several lists, so each list needs enough depth to catch rules whose legalese
# sits far from casual phrasing (observed useful hits down to rank ~50).
_FETCH_K = 60
# Standard RRF damping constant: softens the gap between adjacent ranks so a
# rule at rank 1 in one list doesn't drown out a rule at rank 3 in two lists.
_RRF_K = 60
# Fraction of the best sibling's fused score a rule inherits ("510.1c" and
# "510.1d" share stem "510.1"). Experimental knob: A/B runs on the 27-question
# eval set showed no recall benefit at 0.5, so it defaults off; kept because
# the missed-deciding-sibling pattern is real (see eval Q019) and worth
# revisiting with a larger eval set.
_SIBLING_BOOST = float(os.environ.get("SIBLING_BOOST", "0.0"))

_client: QdrantClient | None = None
_bm25: BM25Okapi | None = None
_bm25_docs: list[dict] | None = None  # type: ignore[type-arg]


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9.]+", text.lower())


def _get_bm25() -> tuple[BM25Okapi, list[dict]]:  # type: ignore[type-arg]
    """Lazily build an in-memory BM25 index over every rule in the collection."""
    global _bm25, _bm25_docs
    if _bm25 is None or _bm25_docs is None:
        docs: list[dict] = []  # type: ignore[type-arg]
        offset = None
        while True:
            points, offset = _get_client().scroll(
                collection_name=COLLECTION_NAME,
                limit=1000,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for pt in points:
                p = pt.payload or {}
                docs.append(
                    {
                        "rule_number": p["rule_number"],
                        "raw_text": p["raw_text"],
                        "examples": p.get("examples", []),
                    }
                )
            if offset is None:
                break
        _bm25_docs = docs
        _bm25 = BM25Okapi([_tokenize(f"{d['rule_number']} {d['raw_text']}") for d in docs])
    return _bm25, _bm25_docs


def _fetch_dense(vec: list[float], limit: int) -> list[dict]:  # type: ignore[type-arg]
    results = _get_client().query_points(
        collection_name=COLLECTION_NAME,
        query=vec,
        limit=limit,
    )
    out = []
    for h in results.points:
        p = h.payload or {}
        out.append(
            {
                "rule_number": p["rule_number"],
                "raw_text": p["raw_text"],
                "score": h.score,
                "examples": p.get("examples", []),
            }
        )
    return out


def _fetch_bm25(query_text: str, limit: int) -> list[dict]:  # type: ignore[type-arg]
    bm25, docs = _get_bm25()
    scores = bm25.get_scores(_tokenize(query_text))
    top = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:limit]
    return [{**docs[i], "score": float(scores[i])} for i in top if scores[i] > 0]


def rules_channel(question: str, *, top_k: int = 5) -> list[dict]:  # type: ignore[type-arg]
    """Return the top-k rules most relevant to the question.

    Each result dict has: rule_number, raw_text, score (RRF fused), examples.
    """
    passages = expand_query(question)
    candidate_lists = [_fetch_dense(embed_text(q), _FETCH_K) for q in [question] + passages]
    candidate_lists.append(_fetch_bm25(" ".join([question] + passages), _FETCH_K))

    fused: dict[str, float] = {}
    payloads: dict[str, dict] = {}  # type: ignore[type-arg]
    for candidates in candidate_lists:
        for rank, c in enumerate(candidates, start=1):
            rn = c["rule_number"]
            fused[rn] = fused.get(rn, 0.0) + 1.0 / (_RRF_K + rank)
            if rn not in payloads:
                payloads[rn] = c

    # Sibling boost: each rule inherits part of the best fused score among the
    # other candidates in its family ("510.1c" and "510.1d" share stem
    # "510.1"; the parent "510.1" itself belongs to the family too).
    def stem(rn: str) -> str:
        return rn.rstrip("abcdefghijklmnopqrstuvwxyz")

    best_by_stem: dict[str, float] = {}
    for rn, score in fused.items():
        s = stem(rn)
        best_by_stem[s] = max(best_by_stem.get(s, 0.0), score)
    boosted = {rn: score + _SIBLING_BOOST * best_by_stem[stem(rn)] for rn, score in fused.items()}

    ranked = sorted(boosted, key=lambda rn: boosted[rn], reverse=True)[:top_k]
    return [{**payloads[rn], "score": boosted[rn]} for rn in ranked]
