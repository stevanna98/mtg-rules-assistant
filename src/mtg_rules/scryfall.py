import httpx
from .config import settings


async def get_card(name: str) -> dict:
    url = f"{settings.scryfall_base_url}/cards/named"
    async with httpx.AsyncClient() as client:
        response = client.get(url, params={"fuzzy": name})
        response.raise_for_status()
        return response.json()


async def search_cards(query: str) -> dict:
    url = f"{settings.scryfall_base_url}/cards/search"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"q": query})
        response.raise_for_status()
        return response.json()
