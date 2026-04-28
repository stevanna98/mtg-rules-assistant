import asyncio

import httpx

from .config import settings

_client: httpx.AsyncClient | None = None
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.scryfall_base_url,
            headers={
                "User-Agent": "mtg-rules-assistant/0.1 (github.com/stevanna98/mtg-rules-assistant)",
                "Accept": "application/json",
            },
            timeout=10.0,
        )
    return _client


async def _rate_limit() -> None:
    global _last_request_time
    async with _rate_limit_lock:
        now = asyncio.get_running_loop().time()
        elapsed = now - _last_request_time
        if elapsed < 0.1:
            await asyncio.sleep(0.1 - elapsed)
        _last_request_time = asyncio.get_running_loop().time()


async def get_card(name: str) -> dict:
    await _rate_limit()
    response = await _get_client().get("/cards/named", params={"fuzzy": name})
    response.raise_for_status()
    return response.json()


async def search_cards(query: str) -> dict:
    await _rate_limit()
    response = await _get_client().get("/cards/search", params={"q": query})
    response.raise_for_status()
    return response.json()


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
