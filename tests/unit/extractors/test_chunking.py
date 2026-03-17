from multiprocessing.context import TimeoutError
from pathlib import Path

import pytest

from kibad_llm.extractors.chunking import _document_chunk_iterator
from kibad_llm.extractors.chunking_utils import RegexTokenizer
from kibad_llm.extractors.chunking_utils.core import TextChunk
from kibad_llm.preprocessing import read_pdf_as_markdown_via_pymupdf4llm
from tests import FIXTURE_DATA_ROOT

FIXTURE_DATA = FIXTURE_DATA_ROOT / "chunking"


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


def test_chunking_timeout() -> None:
    """BMTEN2FG.md is known to be very slow to chunk.
    Chunking it should trigger a timeout, returning None.
    """

    document_from_md = Path("./tests/fixtures/pdfs_error/chunking_fail/BMTEN2FG.md").read_text()

    with pytest.raises(TimeoutError) as e_info:
        _document_chunk_iterator(
            document_from_md,
            20000,
            None,
            1000,
            0.00001,
        )


def test_stride() -> None:
    """x.md is a very simplified version of BMTEN2FG.md with just 233 characters.
    It should not time out.
    """

    document_from_md = (FIXTURE_DATA / "x.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        200,
        None,
        10,
        10,
    )
    # TODO: assert content of chunks


def test_stride_overlaps() -> None:

    document_from_md = Path("./tests/fixtures/pdfs_error/chunking_fail/BMTEN2FG.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        1000,
        None,
        100,
        600,
    )
    previous_chunk = chunks[0].document_text
    assert previous_chunk is not None
    for chunk in chunks[1:]:
        assert chunk.document_text is not None
        for i in range(1, len(previous_chunk) + 1):
            if chunk.document_text.startswith(previous_chunk[i:]):
                break
        else:
            raise ValueError(
                f"chunks not overlapping!\n{previous_chunk}\nthere should be some overlap here\n{chunk.document_text}"
            )
        previous_chunk = chunk.document_text
