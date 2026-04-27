import pytest
from src.mtg_rules.scryfall import get_card


@pytest.mark.asyncio
async def test_lightning_bolt_oracle_text():
    card = await get_card("Lightning Bolt")
    assert "damage" in card["oracle_text"].lower()
