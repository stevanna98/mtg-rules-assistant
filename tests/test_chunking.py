from mtg_rules.chunking import build_chunk_text


def test_chunk_includes_rule_number_and_text() -> None:
    rule = {
        "rule_number": "100.1",
        "parent_number": "100",
        "section": "1",
        "depth": 2,
        "text": "These Magic rules apply to any Magic game.",
        "examples": [],
    }
    parent = {"rule_number": "100", "text": "General"}
    chunk = build_chunk_text(rule, parent)
    assert "[Rule 100.1]" in chunk
    assert "under Rule 100" in chunk
    assert "These Magic rules apply" in chunk


def test_chunk_with_examples() -> None:
    rule = {
        "rule_number": "702.10a",
        "parent_number": "702.10",
        "section": "7",
        "depth": 3,
        "text": "Hexproof from a quality is a variant of the hexproof ability.",
        "examples": ["Hexproof from blue means this permanent can't be the target of blue spells."],
    }
    parent = {"rule_number": "702.10", "text": "Hexproof"}
    chunk = build_chunk_text(rule, parent)
    assert "Example:" in chunk
    assert "blue spells" in chunk


def test_chunk_with_no_parent() -> None:
    rule = {
        "rule_number": "1",
        "parent_number": None,
        "section": "1",
        "depth": 0,
        "text": "Game Concepts",
        "examples": [],
    }
    chunk = build_chunk_text(rule, parent=None)
    assert "[Rule 1]" in chunk
    assert "Game Concepts" in chunk
