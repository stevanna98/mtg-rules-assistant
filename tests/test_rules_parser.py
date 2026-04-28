from pathlib import Path

import pytest

from src.mtg_rules.rules_parser import parse_comprehensive_rules

FIXTURE = """\
Credits

1. Game Concepts

100. General

100.1. These rules apply to any game.

100.1a A two-player game begins with two players.

100.1b A multiplayer game begins with more than two players.
Example: Two people play a two-headed giant match.

2. Parts of a Card

200. General

Glossary

This text should never be parsed.
"""


@pytest.fixture()
def rules_file(tmp_path: Path) -> Path:
    p = tmp_path / "rules.txt"
    p.write_text(FIXTURE, encoding="utf-8")
    return p


def test_parse_count(rules_file: Path) -> None:
    rules = list(parse_comprehensive_rules(rules_file))
    # Expects: 1, 100, 100.1, 100.1a, 100.1b, 2, 200 = 7 rules
    assert len(rules) == 7


def test_lettered_parent(rules_file: Path) -> None:
    rules = {r.rule_number: r for r in parse_comprehensive_rules(rules_file)}
    assert rules["100.1a"].parent_number == "100.1"
    assert rules["100.1a"].depth == 3
    assert rules["100.1a"].section == "1"


def test_example_separated_from_text(rules_file: Path) -> None:
    rules = {r.rule_number: r for r in parse_comprehensive_rules(rules_file)}
    rule = rules["100.1b"]
    assert "Example" not in rule.text
    assert len(rule.examples) == 1
    assert "two-headed giant" in rule.examples[0]


def test_stops_at_glossary(rules_file: Path) -> None:
    rules = {r.rule_number: r for r in parse_comprehensive_rules(rules_file)}
    # "This text should never be parsed" is after Glossary — confirm no extra rules
    assert "Glossary" not in rules
    rule_numbers = set(rules.keys())
    assert rule_numbers == {"1", "100", "100.1", "100.1a", "100.1b", "2", "200"}


def test_depth_levels(rules_file: Path) -> None:
    rules = {r.rule_number: r for r in parse_comprehensive_rules(rules_file)}
    assert rules["1"].depth == 0
    assert rules["100"].depth == 1
    assert rules["100.1"].depth == 2
    assert rules["100.1a"].depth == 3
