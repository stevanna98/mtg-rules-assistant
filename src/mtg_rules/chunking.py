"""Build the text that gets embedded for each rule chunk."""


def build_chunk_text(rule: dict, parent: dict | None) -> str:
    """Construct the text embedded for a rule.

    Format:
      [Rule 702.10a] (under Rule 702.10 — Hexproof, in section 7)
      <rule body>
      Example: <example 1>
    """
    parts: list[str] = []
    rn = rule["rule_number"]
    section = rule.get("section", "")

    header = f"[Rule {rn}]"
    parent_bits: list[str] = []
    if parent is not None:
        parent_summary = parent["text"][:120].rsplit(" ", 1)[0]
        parent_bits.append(f"under Rule {parent['rule_number']} — {parent_summary}")
    if section:
        parent_bits.append(f"in section {section}")
    if parent_bits:
        header = f"{header} ({', '.join(parent_bits)})"
    parts.append(header)

    parts.append(rule["text"])
    for ex in rule.get("examples", []):
        parts.append(f"Example: {ex}")

    return "\n".join(parts)
