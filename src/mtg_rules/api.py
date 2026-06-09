import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncGenerator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .scryfall import close_client, get_card, search_cards
from .answerer import generate_answer
from .retrieval.cards import cards_channel
from .retrieval.rules import rules_channel
from .vision import identify_cards_from_image

_FRONTEND = Path(__file__).parent.parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await close_client()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


class Turn(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    question: str
    # 8 rather than 5: the deciding rule for borderline questions often lands
    # at fused rank 5-8, and eight short rules are still a tiny prompt.
    top_k: int = 8
    history: list[Turn] = []


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/card/{name}")
async def get_card_by_name(name: str):
    try:
        card = await get_card(name)
        return {
            "name": card["name"],
            "mana_cost": card.get("mana_cost"),
            "type_line": card.get("type_line"),
            "oracle_text": card.get("oracle_text"),
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/search")
async def search(q: str):
    try:
        return await search_cards(q)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ask")
async def ask(body: AskRequest):
    """Retrieve rules + cards in parallel, then generate a grounded answer."""
    cards_task = asyncio.create_task(cards_channel(body.question))
    rules = await asyncio.get_event_loop().run_in_executor(
        None, lambda: rules_channel(body.question, top_k=body.top_k)
    )
    cards = await cards_task
    history = [t.model_dump() for t in body.history]
    answer = await generate_answer(body.question, rules, cards, history=history)
    return {
        "question": body.question,
        "answer": answer,
        "rules": rules,
        "cards": cards,
    }


@app.post("/ask/image")
async def ask_with_image(
    question: Annotated[str, Form()],
    image: Annotated[UploadFile, File()],
    top_k: Annotated[int, Form()] = 8,
    history: Annotated[str, Form()] = "[]",
):
    """Like /ask but accepts an image upload for card identification via Groq vision.

    All three channels (vision, text card extraction, rules retrieval) run in parallel.
    Vision-identified and text-identified cards are merged and deduplicated by name.

    history: JSON-encoded list of {"role": "user"|"assistant", "content": str} turns.
    """
    image_bytes = await image.read()
    mime = image.content_type or "image/jpeg"

    vision_task = asyncio.create_task(identify_cards_from_image(image_bytes, mime))
    text_cards_task = asyncio.create_task(cards_channel(question))
    rules = await asyncio.get_event_loop().run_in_executor(
        None, lambda: rules_channel(question, top_k=top_k)
    )

    vision_names, text_cards = await asyncio.gather(vision_task, text_cards_task)

    # Fetch vision-identified cards from Scryfall; drop failures silently
    vision_results = await asyncio.gather(
        *[get_card(n) for n in vision_names], return_exceptions=True
    )
    vision_cards = [r for r in vision_results if not isinstance(r, Exception)]

    # Merge, deduplicate by name (text channel takes priority on duplicates)
    seen: set[str] = set()
    cards = []
    for c in text_cards + vision_cards:
        if c["name"] not in seen:
            seen.add(c["name"])
            cards.append(c)

    history_turns: list[dict] = json.loads(history)  # type: ignore[type-arg]
    answer = await generate_answer(question, rules, cards, history=history_turns)
    return {"question": question, "answer": answer, "rules": rules, "cards": cards}


# Serve the PWA frontend — must be mounted last so API routes take priority.
# The conditional guard prevents a startup error if the frontend dir is absent
# (e.g. running tests before the frontend is built).
if _FRONTEND.is_dir():

    @app.get("/")
    async def serve_index() -> FileResponse:
        return FileResponse(_FRONTEND / "index.html")

    app.mount("/", StaticFiles(directory=str(_FRONTEND)), name="frontend")
