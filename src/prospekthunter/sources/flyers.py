"""Choosing the right reader for a flyer file."""

from pathlib import Path

from prospekthunter.models import Offer
from prospekthunter.sources.rewe import read_rewe_pdf


def read_flyer(path: Path) -> list[Offer]:
    """Read a flyer PDF, using its file name to recognize the retailer."""
    if not path.is_file():
        raise FileNotFoundError(f"flyer not found: {path}")
    if "rewe" in path.name.casefold():
        return read_rewe_pdf(path)
    raise ValueError(f"unsupported flyer: {path.name} (only REWE flyers can be read so far)")
