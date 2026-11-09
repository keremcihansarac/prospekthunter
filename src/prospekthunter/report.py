"""Plain-text report of the offers a user cares about."""

from collections.abc import Mapping, Sequence

from prospekthunter.models import Offer

_MAX_NAME_WIDTH = 60
_MAX_PACKAGE_WIDTH = 26


def format_report(groups: Mapping[str, Sequence[Offer]]) -> str:
    """Render grouped offers as an aligned table with exact dates."""
    offers = [offer for members in groups.values() for offer in members]
    if not offers:
        return "No matching offers found."

    retailer_width = max(len(offer.retailer) for offer in offers)
    name_width = min(max(len(offer.name) for offer in offers), _MAX_NAME_WIDTH)
    package_width = min(max(len(offer.package or "") for offer in offers), _MAX_PACKAGE_WIDTH)

    lines: list[str] = []
    period = _format_period(offers)
    if period is not None:
        lines += [period, ""]

    for category, members in groups.items():
        if not members:
            continue
        lines.append(category)
        for offer in members:
            row = (
                f"  {offer.retailer:<{retailer_width}}"
                f"  {_shorten(offer.name, name_width):<{name_width}}"
                f"  {_format_price(offer):>8}"
                f"  {_shorten(offer.package or '', package_width):<{package_width}}"
                f"  {_format_dates(offer)}"
            )
            lines.append(row + "  (App)" if offer.requires_app else row)
        lines.append("")
    return "\n".join(lines).rstrip()


def _shorten(text: str, width: int) -> str:
    return text if len(text) <= width else f"{text[: width - 1]}…"


def _format_price(offer: Offer) -> str:
    return f"{offer.price:.2f} €".replace(".", ",")


def _format_dates(offer: Offer) -> str:
    start, end = offer.valid_from, offer.valid_until
    if start is not None and end is not None:
        if start == end:
            return f"{start:%d.%m.}"
        return f"{start:%d.%m.} – {end:%d.%m.}"
    if start is not None:
        return f"from {start:%d.%m.}"
    if end is not None:
        return f"until {end:%d.%m.}"
    return "date unknown"


def _format_period(offers: Sequence[Offer]) -> str | None:
    starts = [offer.valid_from for offer in offers if offer.valid_from is not None]
    ends = [offer.valid_until for offer in offers if offer.valid_until is not None]
    if starts and ends:
        return f"{min(starts):%d.%m.%Y} – {max(ends):%d.%m.%Y}"
    if starts:
        return f"from {min(starts):%d.%m.%Y}"
    if ends:
        return f"until {max(ends):%d.%m.%Y}"
    return None
