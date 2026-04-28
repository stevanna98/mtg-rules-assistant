import re
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel

# Matches rules that end with a period: "1.", "100.", "100.1."
_PERIOD_RE = re.compile(r"^(\d{1,3})(\.\d+)?\.\s")
# Matches lettered subrules (no trailing period): "100.1a ", "702.10f "
_LETTER_RE = re.compile(r"^(\d{1,3})(\.\d+)([a-z])\s")


class Rule(BaseModel):
    rule_number: str
    parent_number: str | None
    section: str
    depth: int
    text: str
    examples: list[str]


def _parse_rule_number(line: str) -> str | None:
    m = _LETTER_RE.match(line)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
    m = _PERIOD_RE.match(line)
    if m:
        return m.group(1) + (m.group(2) or "")
    return None


def _parent_and_depth(num: str) -> tuple[str | None, int]:
    if re.match(r"^\d+\.\d+[a-z]$", num):
        return num[:-1], 3  # "702.10a" → parent "702.10", depth 3
    if re.match(r"^\d+\.\d+$", num):
        return num.rsplit(".", 1)[0], 2  # "702.10" → parent "702", depth 2
    if len(num) > 1:
        return num[0], 1  # "702" → parent "7", depth 1
    return None, 0  # "7" → no parent, depth 0


def parse_comprehensive_rules(path: Path) -> Iterator[Rule]:
    """Parse the Comprehensive Rules text file into structured Rule objects.

    Stops parsing when it reaches the Glossary section — glossary handling is a
    separate task for Week 4.
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    # The file starts with a TOC followed by "Glossary" and "Credits".
    # The actual rules body begins after "Credits".
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "Credits":
            start_idx = i + 1
            break

    # Accumulate rule fields in a plain dict to allow mutation, then yield Rule.
    pending: dict | None = None

    def _flush() -> Iterator[Rule]:
        if pending is not None:
            yield Rule(**pending)

    for raw_line in lines[start_idx:]:
        line = raw_line.strip()

        if line == "Glossary":
            break

        if not line:
            continue

        rule_number = _parse_rule_number(line)

        if rule_number is not None:
            yield from _flush()
            rule_text = line[len(rule_number) :].lstrip(". ").strip()
            parent, depth = _parent_and_depth(rule_number)
            pending = {
                "rule_number": rule_number,
                "parent_number": parent,
                "section": rule_number[0],
                "depth": depth,
                "text": rule_text,
                "examples": [],
            }
        elif line.startswith("Example:"):
            if pending is not None:
                pending["examples"].append(line[len("Example:") :].strip())
        else:
            if pending is not None:
                pending["text"] += " " + line

    yield from _flush()


def main() -> None:
    import argparse
    import json  # noqa: F401 — kept for potential future use

    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()

    count = 0
    with args.output.open("w") as f:
        for rule in parse_comprehensive_rules(args.input):
            f.write(rule.model_dump_json() + "\n")
            count += 1

    print(f"Parsed {count} rules → {args.output}")


if __name__ == "__main__":
    main()
