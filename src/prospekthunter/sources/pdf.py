"""Text extraction from flyer PDFs."""

from pathlib import Path

import pypdfium2


def read_page_texts(path: Path) -> list[str]:
    """Return the text of every page in ``path``, in page order."""
    document = pypdfium2.PdfDocument(path)
    try:
        return [document[index].get_textpage().get_text_bounded() for index in range(len(document))]
    finally:
        document.close()
