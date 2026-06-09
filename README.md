---
title: MTG Rules Assistant
emoji: 🧙
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
---

# MTG Rules Assistant

![CI](https://github.com/stevanna98/mtg-rules-assistant/actions/workflows/ci.yml/badge.svg)

A FastAPI service that answers Magic: The Gathering rules questions using the Scryfall API and Claude.

## Setup

```bash
uv sync
```

## Run

```bash
uvicorn mtg_rules.api:app --reload
```

## Docker

```bash
docker build -t mtg-rules-assistant .
docker run -p 8000:8000 --env-file .env mtg-rules-assistant
```

## Live demo

Deployed on Hugging Face Spaces: https://stefanovannoni-mtg-rules-assistant.hf.space

First request after a quiet period may take ~30s while the container wakes up.

## API

| Method | Path          | Description                    |
| ------ | ------------- | ------------------------------ |
| GET    | /health       | Health check                   |
| GET    | /card/{name}  | Look up a card by fuzzy name   |
| GET    | /search?q=... | Search cards by Scryfall query |

## Data pipeline

The Comprehensive Rules are parsed into structured JSONL by:

```bash
uv run python -m mtg_rules.rules_parser data/raw/comprehensive_rules.txt data/processed/rules.jsonl
```

The raw `.txt` and processed `.jsonl` are gitignored — re-generate locally as needed.
The latest rules are available at https://magic.wizards.com/en/rules.

## Local development setup (Week 4+)

Beyond the basic setup, you'll need:

1. A Groq API key in `.env` as `GROQ_API_KEY` (free at console.groq.com)
2. Qdrant running locally:
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
  -v "$(pwd)/data/qdrant_storage:/qdrant/storage" \
  --name qdrant qdrant/qdrant
```
3. Initialize and index the rules collection:
```bash
uv run python scripts/init_qdrant.py
uv run python scripts/index_rules.py
```
4. Sanity-check retrieval:
```bash
uv run python scripts/sanity_check_retrieval.py
```

## Architecture decisions (Week 4)

### Chunking strategy

One Comprehensive Rules entry = one chunk. Each chunk's embedded text includes
the rule number, parent rule context (and parent's text where useful), the rule
body, and any inline examples. The original rule body is preserved separately
in the payload as `raw_text` for citation.

This works because the Comprehensive Rules are already authored as
self-contained, hierarchically-numbered units — the chunking decision most
RAG projects struggle with is gift-wrapped here.

### Embedding model

`all-MiniLM-L6-v2` via sentence-transformers (384 dimensions, cosine distance).
Runs locally — no API key, no rate limits, no cost. Reconsider if recall@10
underperforms in Week 5 evaluation.

### LLM for card name extraction

Groq (Llama 3.3 70B) via the OpenAI-compatible API. Free tier, no billing
required. Used only for the cards channel extraction step (JSON mode — tool
calling proved flaky on Groq and crashed the channel on malformed calls).

## Architecture decisions (retrieval/answering revamp, June 2026)

### Hybrid retrieval with RRF fusion

The rules channel fuses several candidate lists with Reciprocal Rank Fusion:

- dense ANN lists for the raw question AND 2-3 multi-aspect HyDE passages
  (each passage covers a different rules concept implicated by the question);
- one lexical BM25 list (in-memory over all ~3.3k rules), queried with
  question + HyDE passages so the lexical match happens in Comprehensive
  Rules vocabulary rather than casual phrasing.

RRF is scale-free, which fixes the earlier max-score merge where the HyDE
list's higher cosine scores drowned out the raw-question list. HyDE passages
are generated at temperature 0 with a fixed seed (Groq is still not perfectly
deterministic), and any invented rule numbers are stripped before embedding —
they poisoned BM25 otherwise.

### Answering model

`openai/gpt-oss-120b` on Groq (free tier). Llama 3.3 70B produced correct-ish
retrievals but failed multi-step stack reasoning (e.g. it believed Giant
Growth's +3/+3 expires when the spell finishes resolving). The reasoning model
took the LLM-judged answer score from 6/12 to 12/12 on the eval set.

### Evaluation

```bash
uv run python scripts/eval_retrieval.py --k 5   # retrieval recall/MRR
uv run python scripts/eval_answers.py --k 8     # end-to-end LLM-judged answers
```

The answer judge is Llama 3.3 70B (different family from the answerer, to
limit self-preference bias); grades each answer 0-2 against the reference.
