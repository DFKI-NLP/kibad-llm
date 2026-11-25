"""Preprocessing functions for converting input documents to markdown.

Functions:
    read_pdf_as_markdown_via_pymupdf4llm: Read a PDF file and convert it to markdown using pymupdf4llm.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import logging
from pathlib import Path

import pymupdf
import pymupdf4llm

logger = logging.getLogger(__name__)

REPLACEMENT_CHARACTER = "�"


@contextmanager
def _use_cid_for_unknown_unicode() -> Iterator[None]:
    """Temporarily make pymupdf4llm fall back to character codes for glyphs without a Unicode mapping.

    Some PDFs (e.g. older Elsevier papers) embed fonts that have neither a `/ToUnicode` map nor
    standard glyph names. Without `pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE`, MuPDF emits U+FFFD
    (`�`, often displayed as `?`) for every such glyph, so the whole document turns into
    replacement characters. Plain `pymupdf.Page.get_text()` sets this flag by default, but
    `pymupdf4llm.to_markdown` builds its text flags from a hardcoded set without it and offers no
    parameter to add it.

    `pymupdf4llm.to_markdown` reads `pymupdf.TEXT_MEDIABOX_CLIP` at call time when composing its
    text flags, so this context manager ORs the CID flag into that constant and restores it
    afterwards.

    Warning:
        This mutates a module-level constant of `pymupdf` and is therefore not thread-safe. This is
        fine for `datasets.Dataset.map`, which parallelizes via processes, not threads.
    """
    original = pymupdf.TEXT_MEDIABOX_CLIP
    pymupdf.TEXT_MEDIABOX_CLIP = original | pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
    try:
        yield
    finally:
        pymupdf.TEXT_MEDIABOX_CLIP = original


def read_pdf_as_markdown_via_pymupdf4llm(file_name: str, base_path: Path) -> str:
    """Read a PDF file and convert it to markdown using pymupdf4llm.

    Glyphs without a Unicode mapping are emitted as their character code instead of U+FFFD (see
    `_use_cid_for_unknown_unicode`). If replacement characters remain anyway, a warning is logged,
    since the text is then (partially) unreadable for the LLM.

    Args:
        file_name: The name of the PDF file to read.
        base_path: The base path where the PDF file is located.

    Returns:
        The Markdown text.
    """
    with _use_cid_for_unknown_unicode():
        markdown = pymupdf4llm.to_markdown(str(base_path / file_name))

    num_replacement_chars = markdown.count(REPLACEMENT_CHARACTER)
    if num_replacement_chars > 0:
        logger.warning(
            f"{file_name}: extracted markdown contains {num_replacement_chars} Unicode replacement "
            f"characters (U+FFFD) out of {len(markdown)} characters."
        )
    return markdown
