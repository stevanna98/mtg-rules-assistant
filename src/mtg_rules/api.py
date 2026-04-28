from fastapi import FastAPI, HTTPException
from .scryfall import get_card, search_cards
from .config import settings

app = FastAPI(title=settings.app_name)


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
