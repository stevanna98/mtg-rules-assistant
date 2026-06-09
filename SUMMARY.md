# MTG Rules Assistant — Repository Summary

## What It Is

A **Retrieval-Augmented Generation (RAG) system** for answering Magic: The Gathering rules questions. Given a natural-language question (e.g., "Can a creature with hexproof be targeted by its controller?"), the system retrieves relevant official MTG Comprehensive Rules and card data, then generates a grounded, citation-aware answer.

Deployed as a **FastAPI service** on Hugging Face Spaces, with a fully local embedding stack and free-tier LLM inference via Groq.

---

## Directory Structure

```
mtg-rules-assistant/
├── src/mtg_rules/          # Application source code
│   ├── api.py              # FastAPI app + routes
│   ├── config.py           # Pydantic settings (env-based)
│   ├── scryfall.py         # Async Scryfall HTTP client
│   ├── rules_parser.py     # Parse comprehensive_rules.txt → Rule objects
│   ├── embeddings.py       # Sentence-transformers wrapper (384-dim)
│   ├── chunking.py         # Build structured chunk text for embedding
│   ├── query_expansion.py  # HyDE expansion via Groq
│   ├── reranker.py         # Cross-encoder reranker (implemented, not used)
│   ├── answerer.py         # Generate answer via Groq LLM
│   └── retrieval/
│       ├── rules.py        # Qdrant ANN retrieval + dual-embedding merge
│       └── cards.py        # Groq function-calling card extraction + Scryfall fetch
├── scripts/                # Operational and evaluation scripts
├── tests/                  # Pytest tests (11 total)
├── data/
│   ├── eval_set.jsonl      # Benchmark questions
│   └── qdrant_storage/     # Local vector DB (gitignored)
├── .github/workflows/ci.yml
├── Dockerfile
└── pyproject.toml
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check → `{"status": "ok"}` |
| GET | `/card/{name}` | Fetch a card by name from Scryfall (fuzzy match) |
| GET | `/search?q=...` | Full Scryfall search (supports any Scryfall query syntax) |
| POST | `/ask` | **Main endpoint** — full RAG pipeline, returns answer + rules + cards |

---

## The `POST /ask` Pipeline (Core Architecture)

When a question is received, two retrieval channels run **in parallel**:

### Channel 1 — Rules Retrieval (`retrieval/rules.py`)
1. **HyDE expansion** (`query_expansion.py`): Groq Llama 3.3 70B generates a 2–3 sentence hypothetical MTG rules passage that "sounds like" the answer. This bridges the register gap between casual English questions and formal rules legalese.
2. **Dual embedding**: Both the original question and the hypothesis are embedded using `all-MiniLM-L6-v2` (local, 384-dim).
3. **Dual ANN fetch**: Each vector queries Qdrant for `16 × top_k` candidate rules.
4. **Merge by best score**: The two candidate lists are merged, keeping the best score per rule, then sorted. Top `top_k` rules are returned.

### Channel 2 — Card Retrieval (`retrieval/cards.py`)
1. **Card name extraction**: Groq Llama 3.3 70B with **forced function calling** (`register_cards` tool) extracts exact card names from the question, ignoring card types and generic phrases.
2. **Parallel Scryfall fetch**: Each extracted card name is fetched from Scryfall simultaneously via `asyncio.gather()`.

### Answer Generation (`answerer.py`)
Both channels' results are assembled into a structured context block and passed to Groq Llama 3.3 70B with an **MTG judge persona** prompt. The LLM produces a grounded answer with inline rule number citations (e.g., "rule 116.1"). It is instructed to say so clearly rather than guess if context is insufficient.

---

## Data Pipeline (Offline, Run Once)

```
magic.wizards.com → comprehensive_rules.txt
        ↓  rules_parser.py
data/processed/rules.jsonl (~3,292 Rule objects)
        ↓  index_rules.py
Qdrant collection "rules" (384-dim cosine, 3,292 points)
```

**`rules_parser.py`** parses the official plain-text Comprehensive Rules into structured `Rule` Pydantic objects:
- Regex extracts rule numbers (e.g., `702.10a`)
- Hierarchy is inferred: `702.10a` → parent `702.10`, depth 3, section `7`
- Examples (`Example: ...`) are split out from the rule body
- Skips headers/credits, stops at the Glossary

**`chunking.py`** builds the text that gets embedded for each rule. Each chunk includes: rule number, parent context, rule body text, and any examples — encoded as a structured header so the embedding captures hierarchy, not just raw text.

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **HyDE query expansion** | Bridges casual English ↔ rules legalese register gap |
| **Dual embedding merge** | Catches relevant rules that either the raw question or the expanded hypothesis ranks higher |
| **`16 × top_k` fetch multiplier** | Cast a wide ANN net before merging; compensates for lower recall at small k |
| **Reranker disabled** | The cross-encoder (`ms-marco-MiniLM-L-6-v2`) was evaluated but actively demoted semantically relevant rules in favor of surface keyword matches, so it was removed |
| **Groq for LLM calls** | Free-tier inference (Llama 3.3 70B); Claude integration is planned for a later milestone |
| **Local embeddings** | `all-MiniLM-L6-v2` runs on CPU with no API key, keeps costs zero |
| **Lazy singleton clients** | All external connections (Scryfall httpx, Qdrant, Groq) are lazily initialized and globally cached to avoid reconnection overhead |
| **Scryfall rate limiting** | Async lock enforces 100ms gap between requests to stay within API limits |
| **Function calling for card extraction** | Forces structured JSON output from Groq; more reliable than asking for a list in freeform text |

---

## External Dependencies

| Service | Usage | Cost |
|---------|-------|------|
| **Groq API** | Query expansion, card extraction, answer generation (Llama 3.3 70B) | Free tier |
| **Scryfall API** | Card data, oracle text | Free |
| **Qdrant** | Local vector DB (Docker or in-memory) | Free |
| **Hugging Face Spaces** | Hosting/deployment | Free tier |
| **sentence-transformers** | Local embeddings | Free (CPU) |

---

## CI/CD

GitHub Actions runs on every push/PR to `main`:
1. **Lint & test**: ruff (lint + format), mypy (type check), pytest
2. **Docker build**: `docker build -t mtg-rules:ci .`
3. **Deploy** (main only): Git push to Hugging Face Spaces using `HF_TOKEN`

---

## Tests (11 total)

| File | Tests |
|------|-------|
| `test_api.py` | `/health` endpoint returns 200 |
| `test_scryfall.py` | Live fetch of "Lightning Bolt" (integration test) |
| `test_rules_parser.py` | 7 unit tests: parse count, parent linking, example splitting, Glossary stop, depth levels |
| `test_chunking.py` | 3 tests: rule number in chunk, examples included, top-level rule (no parent) |

---

## Evaluation

`data/eval_set.jsonl` contains benchmark questions with 8 fields per entry: `id`, `difficulty` (easy/medium/hard), `category`, `question`, `expected_answer`, `expected_rule_refs`, `expected_card_refs`, `source`.

`scripts/eval_retrieval.py` computes **Recall@k** and **MRR@k** (Mean Reciprocal Rank) over this set by running `rules_channel()` and checking if expected rule prefixes appear in the top-k results.

---

## Roadmap / Pending Work

- **Claude integration** (planned "Week 7"): Replace Groq with Claude for answer generation; `ANTHROPIC_API_KEY` slot already in `.env.example`
- **Git LFS**: `.gitattributes` pre-configured for `*.pt`, `*.onnx`, `*.safetensors` — anticipates fine-tuned model artifacts
- **Glossary handling**: The Glossary section (currently skipped by the parser) is noted for future separate handling
- **Answer quality evaluation**: `eval_set.jsonl` + evaluation harness to benchmark end-to-end answer quality once Claude is integrated
