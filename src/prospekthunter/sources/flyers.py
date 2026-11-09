"""Choosing the right reader for a flyer file."""

import unicodedata
from pathlib import Path

from prospekthunter.models import Offer
from prospekthunter.sources.aldi import read_aldi_pdf
from prospekthunter.sources.rewe import read_rewe_pdf


def read_flyer(path: Path) -> list[Offer]:
    """Read a flyer PDF, using its file name to recognize the retailer."""
    if not path.is_file():
        raise FileNotFoundError(f"flyer not found: {path}")

    # macOS can store umlauts in file names as two separate characters.
    name = unicodedata.normalize("NFC", path.name).casefold()
    if "rewe" in name:
        return read_rewe_pdf(path)
    if "aldi" in name and ("süd" in name or "sued" in name):
        return read_aldi_pdf(path)
    raise ValueError(
        f"unsupported flyer: {path.name} (only REWE and ALDI SÜD flyers can be read so far)"
    )
