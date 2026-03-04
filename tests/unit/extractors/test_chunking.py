from pathlib import Path

from kibad_llm.extractors.chunking import _document_chunk_iterator
from kibad_llm.extractors.chunking_utils import RegexTokenizer
from kibad_llm.preprocessing import read_pdf_as_markdown_via_pymupdf4llm


def test_pdf_as_md_bmten2fg() -> None:
    """currently pymupdf fails to convert BMTEN2FG.pdf properly.

    **IF THIS TEST FAILS**
    Check the converted output of pymupdf for BMTEN2FG.pdf. If it is converted correctly, adapt the test.
    """
    document_from_pdf = read_pdf_as_markdown_via_pymupdf4llm(
        "BMTEN2FG.pdf", Path("./tests/fixtures/pdfs_error/chunking_fail/")
    )
    document_from_md = Path("./tests/fixtures/pdfs_error/chunking_fail/BMTEN2FG.md").read_text()
    assert document_from_md == document_from_pdf


def test_chunking_timout() -> None:
    """BMTEN2FG.md is known to be very slow to chunk.
    Chunking it should trigger a timeout, returning None.
    """

    document_from_md = Path("./tests/fixtures/pdfs_error/chunking_fail/BMTEN2FG.md").read_text()

    assert (
        _document_chunk_iterator(
            document_from_md,
            20000,
            None,
            1000,
            10,
        )
        is None
    )
