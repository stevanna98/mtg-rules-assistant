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
