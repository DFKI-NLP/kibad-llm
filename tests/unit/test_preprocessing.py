"""Tests for `kibad_llm.preprocessing`."""

import json
import logging
from pathlib import Path

import pymupdf

from kibad_llm.config import PROJ_ROOT
from kibad_llm.preprocessing import read_pdf_as_markdown_via_pymupdf4llm
from tests.conftest import WRITE_FIXTURE_DATA


def _write_pdf_without_unicode_mapping(path: Path, text: str) -> None:
    """Write a one-page PDF whose font has no Unicode mapping for its glyphs.

    The page uses a Type1 font with a `/Differences` encoding that assigns non-standard glyph names
    to all characters of `text` and has no `/ToUnicode` map. MuPDF can therefore only recover the
    text via the character codes (`pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE`), otherwise it emits
    U+FFFD for every glyph. This mimics the fonts of affected real-world PDFs (e.g. older Elsevier
    papers).

    Args:
        path: Where to write the PDF.
        text: The (printable ASCII) text to put on the page.
    """
    codes = sorted({ord(c) for c in text})
    differences = " ".join(f"{code} /glyph{code}x" for code in codes)
    doc = pymupdf.open()
    page = doc.new_page()
    font_xref = doc.get_new_xref()
    doc.update_object(
        font_xref,
        "<</Type/Font/Subtype/Type1/BaseFont/Helvetica"
        f"/Encoding<</Type/Encoding/Differences[{differences}]>>>>",
    )
    doc.xref_set_key(page.xref, "Resources", f"<</Font<</F1 {font_xref} 0 R>>>>")
    content_xref = doc.get_new_xref()
    doc.update_object(content_xref, "<<>>")
    doc.update_stream(content_xref, f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode())
    doc.xref_set_key(page.xref, "Contents", f"{content_xref} 0 R")
    doc.save(path)
    doc.close()


def test_read_pdf_as_markdown_via_pymupdf4llm():
    """Markdown of a regular PDF matches the stored fixture."""
    file_name = "25ABQZIH.pdf"

    result = read_pdf_as_markdown_via_pymupdf4llm(
        file_name=file_name, base_path=PROJ_ROOT / "tests" / "fixtures" / "pdfs"
    )

    assert isinstance(result, str)

    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"

    if WRITE_FIXTURE_DATA:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        # write fixture data
        with open(markdown_path, "w") as f:
            json.dump({"text": result}, f, indent=4, ensure_ascii=False)

    # get expected markdown from fixture
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    result_expected = markdown_data["text"]

    assert result == result_expected


def test_read_pdf_as_markdown_via_pymupdf4llm_without_unicode_mapping(tmp_path, caplog):
    """Glyphs without a Unicode mapping are recovered via their character codes, not U+FFFD."""
    text = "Land use-induced changes in raised bog peats"
    _write_pdf_without_unicode_mapping(tmp_path / "no_unicode.pdf", text)
    # sanity check: without the CID fallback, MuPDF cannot decode the text
    with pymupdf.open(tmp_path / "no_unicode.pdf") as doc:
        assert set(doc[0].get_text(flags=pymupdf.TEXT_MEDIABOX_CLIP).strip()) == {"\ufffd"}

    with caplog.at_level(logging.WARNING, logger="kibad_llm.preprocessing"):
        result = read_pdf_as_markdown_via_pymupdf4llm(
            file_name="no_unicode.pdf", base_path=tmp_path
        )

    assert result.strip() == text
    assert caplog.records == []
    # the patched pymupdf constant is restored
    assert not pymupdf.TEXT_MEDIABOX_CLIP & pymupdf.TEXT_CID_FOR_UNKNOWN_UNICODE
