"""End-to-end answer-quality eval against data/eval_set.jsonl.

Runs the full pipeline (query expansion -> hybrid retrieval -> cards channel ->
Groq answerer) for every eval question, then grades each answer with an LLM
judge (llama-3.3-70b on Groq — a different model family from the gpt-oss
answerer, to reduce self-preference bias; judging against a reference answer
is an easier task than answering, so the weaker model suffices).

Grades:
  2  correct verdict AND sound rules reasoning
  1  correct verdict but flawed/missing reasoning, or partially correct
  0  wrong verdict or seriously misleading reasoning

Usage:
  uv run python scripts/eval_answers.py
  uv run python scripts/eval_answers.py --k 8     # retrieval top-k fed to answerer
"""

import argparse
import asyncio
import json
from pathlib import Path

from groq import AsyncGroq

from mtg_rules.answerer import generate_answer
from mtg_rules.config import settings
from mtg_rules.retrieval.cards import cards_channel
from mtg_rules.retrieval.rules import rules_channel

EVAL_PATH = Path("data/eval_set.jsonl")
JUDGE_MODEL = "llama-3.3-70b-versatile"

_JUDGE_PROMPT = """You are grading an MTG rules assistant's answer against a reference answer.

Question: {question}

Reference answer (ground truth): {expected}

Assistant's answer: {answer}

Grade the assistant's answer:
- 2: verdict matches the reference AND the rules reasoning is sound
- 1: verdict matches but the reasoning is flawed or incomplete, or the answer is only partially correct
- 0: verdict contradicts the reference, or the reasoning is seriously misleading

Cited rule numbers need not match the reference; judge the game-rules substance.
Respond with JSON only: {{"grade": <0|1|2>, "reason": "<one sentence>"}}"""


async def grade(client: AsyncGroq, question: str, expected: str, answer: str) -> dict:  # type: ignore[type-arg]
    response = await client.chat.completions.create(
        model=JUDGE_MODEL,
        max_tokens=2048,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": _JUDGE_PROMPT.format(
                    question=question, expected=expected, answer=answer
                ),
            }
        ],
    )
    return json.loads(response.choices[0].message.content or "{}")


async def evaluate(top_k: int) -> None:
    rows = [json.loads(line) for line in EVAL_PATH.read_text().splitlines() if line.strip()]
    client = AsyncGroq(api_key=settings.groq_api_key)
    grades: list[int] = []

    for row in rows:
        q = row["question"]
        cards = await cards_channel(q)
        rules = rules_channel(q, top_k=top_k)
        answer = await generate_answer(q, rules, cards)
        verdict = await grade(client, q, row["expected_answer"], answer)

        g = int(verdict.get("grade", 0))
        grades.append(g)
        print("=" * 90)
        print(f"[{row['id']}] grade={g}  {verdict.get('reason', '')}")
        print(f"  Q: {q}")
        print(f"  A: {answer}")
        print()

    print(f"answer score: {sum(grades)}/{2 * len(grades)}  (grades: {grades})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    asyncio.run(evaluate(args.k))
