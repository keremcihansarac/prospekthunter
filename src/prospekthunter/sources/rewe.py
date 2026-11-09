"""Reader for REWE flyer PDFs.

Each offer is a run of short text lines that ends with a label line ("Aktion") and a
price line. The next product sometimes starts on the price line itself ("0.33 Frisches").
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from prospekthunter.models import Offer
from prospekthunter.sources.pdf import read_page_texts
from prospekthunter.sources.text import clean_line, join_name

RETAILER = "REWE"

_LABELS = {"aktion", "knaller", "tiefpreis"}
_PRICE_LINE = re.compile(r"^(\d{1,3}[.,]\d{2})(?:\s+(.*))?$")
_UNIT_PRICE = re.compile(r"\(\s*1\s*\w+\s*=\s*\d+[.,]\d{2}\s*\)")
_PACKAGE = re.compile(
    r"(?:^|\s)je\s|^je$|\d-(?:g|kg|ml|l)\b|^\d+\s*x\b",
    re.IGNORECASE,
)
_NOISE = re.compile(r"^\d+,\d{2}\s*€$|^bonus$|^zzgl\.|^einzelpreis\b", re.IGNORECASE)
_MARKETING_END = re.compile(r"[!:]$|[^\W\d_]{5,}\.$")
_VALID_FROM = re.compile(r"Gültig ab (\d{2})\.(\d{2})\.(\d{4})")


@dataclass(frozen=True, slots=True)
class _Block:
    name: str
    package: str | None
    price: Decimal


def read_rewe_pdf(path: Path) -> list[Offer]:
    """Read every offer from a REWE flyer PDF."""
    return parse_pages(read_page_texts(path))


def parse_pages(pages: Sequence[str]) -> list[Offer]:
    """Turn the text of a REWE flyer's pages into offers."""
    valid_from, valid_until = _find_validity(pages)
    return [
        Offer(
            retailer=RETAILER,
            name=block.name,
            price=block.price,
            valid_from=valid_from,
            valid_until=valid_until,
            package=block.package,
        )
        for page in pages
        for block in _parse_blocks(page)
    ]


def _find_validity(pages: Sequence[str]) -> tuple[date | None, date | None]:
    """Find the flyer's dates.

    The flyer prints only its first day. It covers one calendar week and shops close on
    Sundays, so the last day is taken to be the Saturday of that week.
    """
    for page in pages:
        match = _VALID_FROM.search(page)
        if match:
            start = date(int(match[3]), int(match[2]), int(match[1]))
            return start, start + timedelta(days=max(5 - start.weekday(), 0))
    return None, None


def _parse_blocks(page: str) -> list[_Block]:
    lines = [clean_line(line) for line in re.split(r"\r?\n", page)]
    blocks: list[_Block] = []
    buffer: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        index += 1
        if not line:
            continue
        if line.casefold() in _LABELS and index < len(lines):
            price_line = _PRICE_LINE.match(lines[index])
            if price_line:
                index += 1
                block = _build_block(buffer, Decimal(price_line[1].replace(",", ".")))
                if block is not None:
                    blocks.append(block)
                buffer = [price_line[2]] if price_line[2] else []
                continue
        buffer.append(line)
    return blocks


def _build_block(lines: Sequence[str], price: Decimal) -> _Block | None:
    """Build one offer from the lines before its price.

    Text order in the PDF is not always reading order, so the lines can start with
    leftovers of another product. A package line closes a product, and whatever follows
    starts a new one unless it begins with "oder", which adds a variant at the same price.
    """
    name_parts: list[str] = []
    package_parts: list[str] = []
    closed = False
    for line in lines:
        if _NOISE.search(line):
            continue
        continues_package = bool(package_parts) and package_parts[-1].endswith("-")
        if continues_package or _UNIT_PRICE.search(line) or _PACKAGE.search(line):
            package = _UNIT_PRICE.sub("", line).strip(" ,")
            if package:
                package_parts.append(package)
            closed = True
            continue
        if _MARKETING_END.search(line):
            name_parts, package_parts, closed = [], [], False
            continue
        if closed and not line.casefold().startswith("oder"):
            name_parts, package_parts = [], []
        closed = False
        name_parts.append(line)

    name = join_name(name_parts)
    name = re.sub(r"^oder\s+", "", name, flags=re.IGNORECASE)
    if not name:
        return None
    return _Block(name=name, package=join_name(package_parts) or None, price=price)
