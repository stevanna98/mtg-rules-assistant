"""Evaluate rules-retrieval recall against data/eval_set.jsonl.

Metrics reported:
  recall@k   — fraction of questions where at least one expected rule prefix
               appears in the top-k results (primary signal)
  mrr@k      — mean reciprocal rank of the first hit within top-k

Usage:
  uv run python scripts/eval_retrieval.py          # default top-k=5
  uv run python scripts/eval_retrieval.py --k 10
"""

import argparse
import json
from pathlib import Path

from mtg_rules.retrieval.rules import rules_channel


EVAL_PATH = Path("data/eval_set.jsonl")


def _hit(rule_number: str, expected_prefixes: list[str]) -> bool:
    return any(rule_number.startswith(p) for p in expected_prefixes)


def evaluate(top_k: int) -> None:
    rows = [json.loads(line) for line in EVAL_PATH.read_text().splitlines() if line.strip()]
    # Keep only questions that have expected rule refs to evaluate against
    rows = [r for r in rows if r.get("expected_rule_refs")]

    if not rows:
        print("No eval rows with expected_rule_refs found.")
        return

    hits = 0
    reciprocal_ranks: list[float] = []

    for row in rows:
        expected = row["expected_rule_refs"]
        results = rules_channel(row["question"], top_k=top_k)
        hit_rank: int | None = None
        for rank, res in enumerate(results, start=1):
            if _hit(res["rule_number"], expected):
                hit_rank = rank
                break

        if hit_rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / hit_rank)
        else:
            reciprocal_ranks.append(0.0)

        status = f"HIT@{hit_rank}" if hit_rank else f"MISS (top-{top_k})"
        print(f"[{row['id']}] {status}  expected={expected}")
        for res in results:
            marker = "  *" if _hit(res["rule_number"], expected) else "   "
            print(f"{marker} {res['score']:.3f}  {res['rule_number']}  {res['raw_text'][:70]}")
        print()

    recall = hits / len(rows)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)
    print(f"recall@{top_k}: {recall:.2f}  ({hits}/{len(rows)})")
    print(f"mrr@{top_k}:    {mrr:.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    evaluate(args.k)
