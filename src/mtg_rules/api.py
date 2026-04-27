from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .scryfall import get_card, search_cards
from .config import settings

app = FastAPI(title=settings.app_name)


class CardQuery(BaseModel):
    name: str


class SearchQuery(BaseModel):
    query: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/card")
async def card(body: CardQuery):
    try:
        return await get_card(body.name)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/search")
async def search(body: SearchQuery):
    try:
        return await search_cards(body.query)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
