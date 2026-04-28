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

## API

| Method | Path          | Description                    |
| ------ | ------------- | ------------------------------ |
| GET    | /health       | Health check                   |
| GET    | /card/{name}  | Look up a card by fuzzy name   |
| GET    | /search?q=... | Search cards by Scryfall query |
