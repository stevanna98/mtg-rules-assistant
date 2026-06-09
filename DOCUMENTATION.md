# MTG Rules Assistant — Full Documentation

## Table of Contents

1. [What This Project Is](#1-what-this-project-is)
2. [Architecture Overview](#2-architecture-overview)
3. [Repository Structure](#3-repository-structure)
4. [Installation & Setup](#4-installation--setup)
5. [Running the App](#5-running-the-app)
6. [API Reference](#6-api-reference)
7. [Data Pipeline](#7-data-pipeline)
8. [Testing](#8-testing)
9. [Linting & Type Checking](#9-linting--type-checking)
10. [Docker](#10-docker)
11. [CI/CD & Deployment](#11-cicd--deployment)
12. [Configuration & Environment Variables](#12-configuration--environment-variables)
13. [Module Reference](#13-module-reference)
14. [Evaluation Set](#14-evaluation-set)
15. [Roadmap Notes](#15-roadmap-notes)

---

## 1. What This Project Is

**MTG Rules Assistant** is a FastAPI web service that helps players look up *Magic: The Gathering* card information and rules. It exposes a simple REST API that:

- Fetches card data (mana cost, type line, oracle text) from the [Scryfall API](https://scryfall.com/docs/api) using fuzzy name matching.
- Supports arbitrary Scryfall query-syntax searches.
- Serves a health-check endpoint for container orchestration.

The project also includes a standalone **Comprehensive Rules parser** that converts the official MTG rules text file (9 000+ lines) into a structured JSONL dataset of 3 292 individual rules, each with metadata such as rule number, depth level, parent rule, and extracted examples.

The app is packaged as a Docker image and deployed automatically to [Hugging Face Spaces](https://stefanovannoni-mtg-rules-assistant.hf.space) on every push to `main`.

> **Claude integration is not yet implemented.** The `.env.example` notes it is planned for a future milestone ("Week 7"). The current service only calls Scryfall.

---

## 2. Architecture Overview

```
Client
  │
  ▼
FastAPI app  (src/mtg_rules/api.py)
  │
  ├── GET /health          → static JSON response
  ├── GET /card/{name}     → ScryfallClient.get_card()
  └── GET /search?q=...    → ScryfallClient.search_cards()
          │
          ▼
     Scryfall API (https://api.scryfall.com)
          │
          ▼
     httpx async client   (src/mtg_rules/scryfall.py)
       • 100 ms rate-limit between requests
       • 10 s request timeout
       • graceful shutdown via FastAPI lifespan
```

The rules parser is a separate CLI tool and does not run as part of the web service — it is used offline to pre-process the rules text file into JSONL.

```
data/raw/comprehensive_rules.txt
        │
        ▼
  rules_parser.py  (CLI / importable module)
        │
        ▼
data/processed/rules.jsonl
```

---

## 3. Repository Structure

```
mtg-rules-assistant/
│
├── src/
│   └── mtg_rules/
│       ├── __init__.py          # Empty package marker
│       ├── config.py            # Pydantic-settings config object
│       ├── api.py               # FastAPI application & route handlers
│       ├── scryfall.py          # Async Scryfall API client
│       └── rules_parser.py      # Comprehensive Rules text → JSONL parser
│
├── tests/
│   ├── test_api.py              # Health-check endpoint test
│   ├── test_scryfall.py         # Live Scryfall integration test
│   └── test_rules_parser.py     # 7 unit tests for the rules parser
│
├── data/
│   ├── eval_set.jsonl           # Benchmark evaluation questions
│   ├── raw/
│   │   └── comprehensive_rules.txt   # Official MTG rules (gitignored)
│   └── processed/
│       └── rules.jsonl               # Parsed rules output (gitignored)
│
├── .github/
│   └── workflows/
│       └── ci.yml               # Lint → test → Docker build → HF deploy
│
├── Dockerfile                   # Multi-stage Python 3.12 image
├── .dockerignore
├── .gitignore
├── .gitattributes               # Git LFS filters for ML model files
├── .env.example                 # Template for environment variables
├── pyproject.toml               # Project metadata, deps, tool config
├── uv.lock                      # Locked dependency tree
└── README.md                    # Hugging Face Spaces config + quick start
```

> `data/raw/*` and `data/processed/*` are gitignored. Only the `.gitkeep` placeholders are committed.

---

## 4. Installation & Setup

### Prerequisites

- **Python 3.11+**
- **[uv](https://github.com/astral-sh/uv)** — the package manager used by this project

Install `uv` if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone & install

```bash
git clone https://github.com/stevanna98/mtg-rules-assistant.git
cd mtg-rules-assistant

# Create the virtual environment and install all dependencies (including dev)
uv sync
```

### Environment variables

```bash
cp .env.example .env
# Edit .env as needed (no required variables yet)
```

---

## 5. Running the App

### Development (with auto-reload)

```bash
uv run uvicorn mtg_rules.api:app --reload
```

The server starts at `http://127.0.0.1:8000`.

### Production (explicit host/port)

```bash
uv run uvicorn src.mtg_rules.api:app --host 0.0.0.0 --port 8000
```

### Interactive API docs

Once running, visit:

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

---

## 6. API Reference

### `GET /health`

Returns a simple health-check response. Used by container orchestration systems to verify the service is alive.

**Response**

```json
{ "status": "ok" }
```

---

### `GET /card/{name}`

Looks up a single card by name using Scryfall's fuzzy matching. Partial names and misspellings are handled gracefully.

**Path parameter**

| Parameter | Type   | Description                          |
|-----------|--------|--------------------------------------|
| `name`    | string | Card name (fuzzy matched by Scryfall) |

**Success response (200)**

```json
{
  "name": "Lightning Bolt",
  "mana_cost": "{R}",
  "type_line": "Instant",
  "oracle_text": "Lightning Bolt deals 3 damage to any target."
}
```

**Error responses**

| Code | Condition                      |
|------|-------------------------------|
| 404  | Card not found by Scryfall     |
| 500  | Unexpected error from Scryfall |

---

### `GET /search`

Performs a full Scryfall search using [Scryfall query syntax](https://scryfall.com/docs/syntax).

**Query parameter**

| Parameter | Type   | Description                        |
|-----------|--------|------------------------------------|
| `q`       | string | Scryfall search query string        |

**Example request**

```
GET /search?q=t:instant+cmc=1+c:r
```

**Success response (200)**

Returns a list of card objects in the same shape as `/card/{name}`.

```json
[
  {
    "name": "Lightning Bolt",
    "mana_cost": "{R}",
    "type_line": "Instant",
    "oracle_text": "Lightning Bolt deals 3 damage to any target."
  },
  ...
]
```

**Error responses**

| Code | Condition                                 |
|------|------------------------------------------|
| 400  | Search query rejected or no results found |

---

## 7. Data Pipeline

The raw MTG Comprehensive Rules are distributed as a plain-text file by Wizards of the Coast. The parser converts this file into a structured JSONL dataset.

### Getting the raw rules

Download the latest rules from:
`https://magic.wizards.com/en/rules`

Save the file to `data/raw/comprehensive_rules.txt`.

### Running the parser

```bash
uv run python -m mtg_rules.rules_parser \
  data/raw/comprehensive_rules.txt \
  data/processed/rules.jsonl
```

### Output format

Each line of `rules.jsonl` is a JSON object representing one rule:

```json
{
  "rule_number": "100.1a",
  "parent_number": "100.1",
  "section": "1",
  "depth": 3,
  "text": "A two-player game is a game that begins with only two players.",
  "examples": []
}
```

| Field           | Type            | Description                                              |
|-----------------|-----------------|----------------------------------------------------------|
| `rule_number`   | string          | The rule's identifier, e.g. `"702.10"`, `"100.1a"`      |
| `parent_number` | string or null  | The direct parent rule's number                          |
| `section`       | string          | Top-level section digit (`"1"` through `"9"`)            |
| `depth`         | int (0–3)       | 0 = section header, 1 = subsection, 2 = rule, 3 = lettered sub-rule |
| `text`          | string          | The rule text, without examples                          |
| `examples`      | list of strings | Examples extracted from the rule text (prefixed "Example:") |

The parser produces **3 292 rules** from the April 2026 edition of the rules.

### Parser behavior

- Skips the table of contents.
- Stops parsing when it reaches the "Glossary" section.
- Regex-matches numbered rules (e.g. `100`, `100.1`, `100.1a`).
- Computes `parent_number` by walking up the rule-number hierarchy.
- Splits `Example:` text out of the rule body into the `examples` list.

---

## 8. Testing

```bash
# Run all tests with verbose output
uv run pytest -v
```

### Test files

| File                        | What it tests                                         |
|-----------------------------|-------------------------------------------------------|
| `tests/test_api.py`         | `GET /health` returns `200 {"status": "ok"}`          |
| `tests/test_scryfall.py`    | Live Scryfall call for "Lightning Bolt" (integration) |
| `tests/test_rules_parser.py`| 7 unit tests covering rule count, depth, parent linking, example extraction, and glossary stop |

Tests use `pytest-asyncio` in `auto` mode, so async test functions work without decorators.

> `test_scryfall.py` makes a real HTTP request to Scryfall. It will fail if you are offline.

---

## 9. Linting & Type Checking

```bash
# Lint (check only)
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Check formatting
uv run ruff format --check src/ tests/

# Apply formatting
uv run ruff format src/ tests/

# Static type checking
uv run mypy src/
```

Ruff is configured in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
```

---

## 10. Docker

### Build the image

```bash
docker build -t mtg-rules-assistant .
```

The Dockerfile uses a **two-stage build**:

1. **Builder**: installs `uv` and runs `uv sync --frozen --no-dev` to produce a clean virtual environment.
2. **Runtime**: creates a non-root `app` user, copies only the virtual environment, and runs uvicorn.

### Run the container

```bash
docker run -p 8000:8000 --env-file .env mtg-rules-assistant
```

The container listens on port `8000`. Map it to any host port you prefer.

---

## 11. CI/CD & Deployment

The GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and pull request to `main`.

### Pipeline stages

```
push / PR to main
    │
    ├── lint-and-test (ubuntu-latest)
    │     ├── ruff check (lint)
    │     ├── ruff format --check
    │     ├── mypy (type check)
    │     └── pytest -v
    │
    ├── docker-build (ubuntu-latest)
    │     └── docker build -t mtg-rules:ci .
    │
    └── deploy-hf  (push to main only, after both above pass)
          └── git push → huggingface.co/spaces/stefanovannoni/mtg-rules-assistant
```

### Secrets required

| Secret     | Purpose                                    |
|------------|--------------------------------------------|
| `HF_TOKEN` | Hugging Face write token for Space deploy  |

### Live deployment

The deployed service is available at:
`https://stefanovannoni-mtg-rules-assistant.hf.space`

---

## 12. Configuration & Environment Variables

Configuration is handled by `src/mtg_rules/config.py` using `pydantic-settings`. Values are read from the `.env` file and environment variables.

| Variable            | Default                        | Description                    |
|---------------------|--------------------------------|--------------------------------|
| `APP_NAME`          | `"MTG Rules Assistant"`        | Application name               |
| `SCRYFALL_BASE_URL` | `"https://api.scryfall.com"`   | Base URL for Scryfall API calls |

No variables are currently required — the defaults are sufficient to run the app.

> An `ANTHROPIC_API_KEY` variable will be added in a future milestone when Claude integration is implemented.

---

## 13. Module Reference

### `src/mtg_rules/config.py`

Exports a singleton `settings` object of type `Settings`. Import it anywhere you need configuration:

```python
from mtg_rules.config import settings
print(settings.scryfall_base_url)
```

---

### `src/mtg_rules/scryfall.py`

Async Scryfall API client. Key functions:

```python
async def get_card(name: str) -> dict
```
Returns raw Scryfall card JSON for the closest fuzzy match to `name`. Raises `httpx.HTTPStatusError` on failure.

```python
async def search_cards(query: str) -> list[dict]
```
Returns a list of Scryfall card JSON objects matching the query.

```python
async def close_client() -> None
```
Closes the shared `httpx.AsyncClient`. Called automatically on app shutdown via the FastAPI lifespan handler.

**Rate limiting**: a 0.1-second gap is enforced between consecutive requests. **Timeout**: 10 seconds per request.

---

### `src/mtg_rules/api.py`

The FastAPI application instance is `app`. It is importable for testing or mounting into a larger application:

```python
from mtg_rules.api import app
```

The lifespan context manager ensures `close_client()` is called on shutdown regardless of how the process exits.

---

### `src/mtg_rules/rules_parser.py`

The `Rule` Pydantic model and the `parse_rules(text: str) -> list[Rule]` function are the main public API. The `main()` function wires up the CLI.

```python
from mtg_rules.rules_parser import parse_rules

with open("data/raw/comprehensive_rules.txt") as f:
    rules = parse_rules(f.read())

print(len(rules))       # 3292
print(rules[0].model_dump())
```

---

## 14. Evaluation Set

`data/eval_set.jsonl` contains benchmark questions for evaluating future Claude-powered answers. Each record follows this schema:

```json
{
  "id": "001",
  "difficulty": "easy",
  "category": "single_card",
  "question": "Does a creature with haste still have summoning sickness for tapping abilities?",
  "expected_answer": "Yes. Haste only allows attacking and using tap abilities; summoning sickness for activated tap abilities is unaffected by haste.",
  "expected_rule_refs": ["302.1", "702.10"],
  "expected_card_refs": [],
  "source": "https://reddit.com/r/askajudge/..."
}
```

| Field                | Description                                          |
|----------------------|------------------------------------------------------|
| `id`                 | Unique question identifier                           |
| `difficulty`         | `easy` / `medium` / `hard`                           |
| `category`           | Question category (e.g. `single_card`, `interaction`) |
| `question`           | The question as a user would ask it                  |
| `expected_answer`    | Reference answer for evaluation                      |
| `expected_rule_refs` | Rule numbers the correct answer should cite          |
| `expected_card_refs` | Card names the answer should reference (if any)      |
| `source`             | Where the question/answer was sourced from           |

---

## 15. Roadmap Notes

Based on comments in the codebase:

- **Claude integration** — the `.env.example` notes `ANTHROPIC_API_KEY` will be added in "Week 7". Once added, the assistant will use Claude to answer rules questions using the parsed `rules.jsonl` as context.
- **Git LFS** — `.gitattributes` is pre-configured for ML model files (`*.pt`, `*.onnx`, `*.safetensors`), anticipating future fine-tuned or embedded model storage.
- **Evaluation harness** — the `eval_set.jsonl` will be used to benchmark answer quality once the Claude integration is live.
