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
required. Used only for the cards channel extraction step; a more capable model
will be evaluated for the answering layer in Week 7.
