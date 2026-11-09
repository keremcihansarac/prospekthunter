"""Text clean-up shared by the flyer readers."""

from collections.abc import Sequence


def clean_line(line: str) -> str:
    """Restore hyphens reported as a control character and remove soft hyphens."""
    return line.replace("\x02", "-").replace("\xad", "").strip()


def join_name(parts: Sequence[str]) -> str:
    """Join lines, repairing words that a line break split with a hyphen."""
    name = ""
    for part in parts:
        if name.endswith("-"):
            # A capital starts a new word of a compound, lower case continues the same word.
            name = name + part if part[:1].isupper() else name[:-1] + part
        else:
            name = f"{name} {part}".strip()
    return name.strip(" ,")
