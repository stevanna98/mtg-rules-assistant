from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException

from .config import settings
from .scryfall import close_client, get_card, search_cards


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await close_client()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


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
