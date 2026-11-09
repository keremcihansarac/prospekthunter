"""Reader for ALDI SÜD flyer PDFs.

An offer is a run of short lines: brand, product name, details such as "400-g-Packung;",
then a price. The price is usually split over two lines, as "4." and "69*". Validity is
printed once per page, without a year.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from prospekthunter.models import Offer
from prospekthunter.sources.pdf import read_page_texts
from prospekthunter.sources.text import clean_line, join_name

RETAILER = "ALDI SÜD"

_MAX_NAME_LINES = 4
_MAX_NAME_LINE_LENGTH = 45

_WEEKDAY = r"(?:Mo|Di|Mi|Do|Fr|Sa)\."
_DAY_MONTH = r"(\d{1,2})\.(\d{1,2})\."
_RANGE = re.compile(rf"{_WEEKDAY}\s*{_DAY_MONTH}\s*[–-]\s*{_WEEKDAY}\s*{_DAY_MONTH}")
_STARTING = re.compile(rf"\bab\s+{_WEEKDAY}\s*{_DAY_MONTH}")

_PRICE_EUROS = re.compile(r"^(\d{1,3})\.$")
_PRICE_CENTS = re.compile(r"^(\d{2})(?:\*{0,2}$|\*{1,2}\s+(.*)$)")
_PRICE_WHOLE = re.compile(r"^(\d{1,3}\.\d{2})(?:\*{1,2}| bzw\. \d{1,3}\.\d{2}\*{0,2})$")

_NOISE = re.compile(
    r"KI-generiert|^Aktion$|^-\d+\s*%$|^XXL$|^-?\d+\.\d{2}(?:\d\.\d{2})?$|^zzgl\."
    r"|^ab \d+\.\d{2}$|KAUFE \d",
    re.IGNORECASE,
)
_DETAIL = re.compile(
    r";|/$|,$|\d-(?:g|kg|ml|l)-|(?:kg|l|m)-Preis|^Versch\.|^je\s|^\d+\s*x\s|^Ursprung:"
    r"|Abtropf|^bzw\."
)
_SECTION_TAG = re.compile(r"[A-ZÄÖÜ-]{4,}")
_NAME_STOP = re.compile(r"^•|[.!:–]$|\.de\b")
_NAME_FRAGMENT = re.compile(rf"^(?:\d{{2}}\*+\s+|ab\s+{_WEEKDAY}\s*\d{{1,2}}\.\d{{1,2}}\.\s+)")
_SIZE = re.compile(r"(?:(\d+)\s*x\s*)?(\d+(?:,\d+)?)-(g|kg|ml|l)-", re.IGNORECASE)
_UNIT_PRICE = re.compile(r"(?:kg|l)-Preis\s*(\d+\.\d{2})")
_PRICE_TOLERANCE = Decimal("0.04")
_PACKAGE = re.compile(
    r"(?:je\s+)?(?:\d+\s*x\s*\d+(?:,\d+)?\s*g\s*=\s*)?\d+(?:,\d+)?-(?:g|kg|ml|l)-\s?[\wäöüÄÖÜß.-]*"
    r"|\bje Stück\b|\bStück\b"
)


@dataclass(frozen=True, slots=True)
class _Block:
    name: str
    package: str | None
    price: Decimal


def read_aldi_pdf(path: Path) -> list[Offer]:
    """Read every offer from an ALDI SÜD flyer PDF."""
    return parse_pages(read_page_texts(path), today=date.today())


def parse_pages(pages: Sequence[str], today: date) -> list[Offer]:
    """Turn the text of an ALDI SÜD flyer's pages into offers.

    ``today`` supplies the year, which the flyer does not print.
    """
    offers: list[Offer] = []
    for page in pages:
        valid_from, valid_until = _page_validity(page, today)
        offers += [
            Offer(
                retailer=RETAILER,
                name=block.name,
                price=block.price,
                valid_from=valid_from,
                valid_until=valid_until,
                package=block.package,
            )
            for block in _parse_blocks(page)
        ]
    return offers


def _page_validity(page: str, today: date) -> tuple[date | None, date | None]:
    """Return the page's validity, or nothing when the page does not state exactly one.

    A page with several labels mixes offers, and guessing could show a wrong date.
    """
    found: set[tuple[date, date | None]] = set()
    for match in _RANGE.finditer(page):
        start = _resolve_date(match[1], match[2], today)
        end = _resolve_date(match[3], match[4], today)
        if start is not None and end is not None:
            found.add((start, end))
    for match in _STARTING.finditer(_RANGE.sub(" ", page)):
        start = _resolve_date(match[1], match[2], today)
        if start is not None:
            found.add((start, None))
    if len(found) != 1:
        return None, None
    return found.pop()


def _resolve_date(day: str, month: str, today: date) -> date | None:
    """Pick the year that puts the date closest to today. Impossible dates give ``None``."""
    candidates: list[date] = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            candidates.append(date(year, int(month), int(day)))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda candidate: abs((candidate - today).days))


def _read_price(lines: Sequence[str], index: int) -> tuple[Decimal, int, str | None] | None:
    """Return the price at ``index``, the lines it uses, and any text that follows it.

    The next product sometimes starts on the same line as the cents ("99* HARIBO").
    """
    whole = _PRICE_WHOLE.match(lines[index])
    if whole:
        return Decimal(whole[1]), 1, None
    euros = _PRICE_EUROS.match(lines[index])
    if euros and index + 1 < len(lines):
        cents = _PRICE_CENTS.match(lines[index + 1])
        if cents:
            return Decimal(f"{euros[1]}.{cents[1]}"), 2, cents[2]
    return None


def _parse_blocks(page: str) -> list[_Block]:
    lines = [clean_line(line) for line in re.split(r"\r?\n", page)]
    blocks: list[_Block] = []
    buffer: list[str] = []
    index = 0
    while index < len(lines):
        if not lines[index]:
            index += 1
            continue
        price = _read_price(lines, index)
        if price is None:
            buffer.append(lines[index])
            index += 1
            continue
        block = _build_block(buffer, price[0])
        if block is not None:
            blocks.append(block)
        buffer = [price[2]] if price[2] else []
        index += price[1]
    return blocks


def _build_block(lines: Sequence[str], price: Decimal) -> _Block | None:
    """Build one offer from the lines before its price.

    Detail lines close a product. A later plain line means those details belonged to
    another product, so the block starts again. Short capitalized section labels such as
    "KÜHLUNG" appear between the details and the price and are skipped.
    """
    name_parts: list[str] = []
    details: list[str] = []
    for line in lines:
        if _NOISE.search(line):
            continue
        if _DETAIL.search(line):
            details.append(line)
            continue
        if details:
            if _SECTION_TAG.fullmatch(line):
                continue
            name_parts, details = [], []
        name_parts.append(line)

    name = _NAME_FRAGMENT.sub("", join_name(_trim_name(name_parts)))
    if not name or not details or not _price_matches_details(details, price):
        return None
    return _Block(name=name, package=_find_package(details), price=price)


def _price_matches_details(details: Sequence[str], price: Decimal) -> bool:
    """Check the price against package size and unit price when they are unambiguous.

    PDF text order can attach a price to the wrong product. Showing a wrong price is worse
    than leaving an offer out. Offers with variants or drained weight cannot be checked
    this way and are accepted.
    """
    text = " ".join(details)
    if "Abtropf" in text or "bzw." in text:
        return True
    sizes = _SIZE.findall(text)
    unit_prices = _UNIT_PRICE.findall(text)
    if len(sizes) != 1 or len(unit_prices) != 1:
        return True

    count, amount, unit = sizes[0]
    quantity = Decimal(amount.replace(",", ".")) * (int(count) if count else 1)
    if unit.casefold() in {"g", "ml"}:
        quantity /= 1000
    expected = Decimal(unit_prices[0]) * quantity
    return abs(price - expected) <= expected * _PRICE_TOLERANCE


def _trim_name(parts: Sequence[str]) -> list[str]:
    """Keep the lines directly before the details, stopping at advertising text."""
    kept: list[str] = []
    for line in reversed(parts):
        if (
            len(kept) == _MAX_NAME_LINES
            or len(line) > _MAX_NAME_LINE_LENGTH
            or _NAME_STOP.search(line)
        ):
            break
        kept.append(line)
    kept.reverse()
    return kept


def _find_package(details: Sequence[str]) -> str | None:
    match = _PACKAGE.search(" ".join(details))
    return match[0].strip(" ;,") if match else None
