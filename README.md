---
title: Mtg Rules Assistant
emoji: 🌖
colorFrom: indigo
colorTo: green
sdk: docker
pinned: false
license: mit
---

# MTG Rules Assistant

A FastAPI service that answers Magic: The Gathering rules questions using the Scryfall API and Claude.

## Setup

```bash
pip install -e ".[dev]"
```

Create a `.env` file:

```
ANTHROPIC_API_KEY=your_key_here
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

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/card` | Look up a card by name |
| POST | `/search` | Search cards by Scryfall query |
