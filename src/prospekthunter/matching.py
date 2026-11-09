"""Deciding which product group an offer belongs to."""

import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from prospekthunter.categories import Category
from prospekthunter.models import Offer

_WORD_CHAR = r"[^\W_]"
_ANY_LETTERS = rf"{_WORD_CHAR}*"
_WORD_SEPARATOR = r"[\s-]+"


def normalize(text: str) -> str:
    """Bring text into one form, so PDF quirks and letter case cannot affect matching.

    NFKC resolves PDF ligatures such as "ﬁ" and decomposed umlauts. Case folding turns
    "ß" into "ss", which makes "Eiweiß" and "Eiweiss" equal.
    """
    cleaned = unicodedata.normalize("NFKC", text).replace("­", "").replace("‐", "-")
    return " ".join(cleaned.casefold().split())


def _variants(text: str) -> tuple[str, ...]:
    """Return the text as printed and with line-break hyphens joined.

    Flyers break compounds across lines, so "Hüttenkä- se" must also be read as one word.
    """
    normalized = normalize(text)
    joined = normalized.replace("- ", "")
    return (normalized, joined) if joined != normalized else (normalized,)


def _compile_word(word: str, term: str) -> str:
    core = word.strip("*")
    if not core or "*" in core:
        raise ValueError(f"invalid term {term!r}: use * only at the start or end of a word")
    prefix = _ANY_LETTERS if word.startswith("*") else ""
    suffix = _ANY_LETTERS if word.endswith("*") else ""
    return f"{prefix}{re.escape(core)}{suffix}"


def _compile_term(term: str) -> str:
    words = [word for word in re.split(_WORD_SEPARATOR, normalize(term)) if word]
    if not words:
        raise ValueError(f"invalid term {term!r}: it contains no words")
    body = _WORD_SEPARATOR.join(_compile_word(word, term) for word in words)
    return rf"(?<!{_WORD_CHAR}){body}(?!{_WORD_CHAR})"


def _compile_terms(terms: Sequence[str]) -> re.Pattern[str] | None:
    if not terms:
        return None
    return re.compile("|".join(_compile_term(term) for term in terms))


@dataclass(frozen=True, slots=True)
class _CompiledCategory:
    category: Category
    include: re.Pattern[str] | None
    exclude: re.Pattern[str] | None

    def accepts(self, variants: tuple[str, ...]) -> bool:
        if self.exclude is not None and any(self.exclude.search(text) for text in variants):
            return False
        return self.include is not None and any(self.include.search(text) for text in variants)


class CategoryMatcher:
    """Assigns text to the first category that accepts it.

    Category order decides ties, so a "High Protein Hähnchen" meal appears once, under
    the earlier group. Being excluded from one group does not rule out a later group.
    """

    def __init__(self, categories: Sequence[Category]) -> None:
        self._categories = tuple(
            _CompiledCategory(
                category=category,
                include=_compile_terms(category.include),
                exclude=_compile_terms(category.exclude),
            )
            for category in categories
        )

    def match(self, text: str) -> Category | None:
        """Return the category for ``text``, or ``None`` if no category wants it."""
        variants = _variants(text)
        for compiled in self._categories:
            if compiled.accepts(variants):
                return compiled.category
        return None

    def group_offers(self, offers: Iterable[Offer]) -> dict[str, list[Offer]]:
        """Group matching offers by category name, in category order, without empty groups."""
        groups: dict[str, list[Offer]] = {
            compiled.category.name: [] for compiled in self._categories
        }
        for offer in offers:
            category = self.match(offer.name)
            if category is not None:
                groups[category.name].append(offer)
        return {name: members for name, members in groups.items() if members}
