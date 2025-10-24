from __future__ import annotations

import logging
from pathlib import Path

import pymupdf4llm

logger = logging.getLogger(__name__)


def read_pdf_as_markdown_via_pymupdf4llm(file_name: str, base_path: Path) -> str:
    """Read a PDF file and convert it to markdown using pymupdf4llm.

    Args:
        file_name: The name of the PDF file to read.
        base_path: The base path where the PDF file is located.
    Returns:
        The Markdown text.
    """
    return pymupdf4llm.to_markdown(str(base_path / file_name))
