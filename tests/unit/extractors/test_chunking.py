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

    The overlap is "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD", as it is smaller than 100 characters.
    The overlap is not "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
    because that would be 101 characters, which is more than the stride of 100.
    """

    document_from_md = (FIXTURE_DATA / "x.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        200,
        None,
        100,
        10,
    )
    for predict, gold in zip(
        chunks,
        [
            "AAAAAAAAAAAAAAA BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
            "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
        ],
    ):
        assert predict.chunk_text == gold


def test_stride_no_overlap() -> None:
    """x.md is a very simplified version of BMTEN2FG.md with just 233 characters.
    It should not time out.

    There is no overlap because the stride of 10 characters is smaller than the last token
    "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD", which is 46 characters.
    """

    document_from_md = (FIXTURE_DATA / "x.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        200,
        None,
        10,
        10,
    )
    for predict, gold in zip(
        chunks,
        [
            "AAAAAAAAAAAAAAA BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
            "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
        ],
    ):
        assert predict.chunk_text == gold


def test_stride_overlaps() -> None:
    """This tests for overlapping chunks."""

    document_from_md = Path("./tests/fixtures/pdfs_error/chunking_fail/BMTEN2FG.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        1000,
        None,
        100,
        600,
    )
    previous_chunk = chunks[0].chunk_text
    for chunk in chunks[1:]:
        assert previous_chunk is not None
        assert chunk.chunk_text is not None
        # chunks should overlap at least ten characters
        for i in range(0, len(previous_chunk) - 10):
            if chunk.chunk_text.startswith(previous_chunk[i:]):
                break
        else:
            raise ValueError(
                f"chunks not overlapping!\n{previous_chunk}\nthere should be some overlap here\n{chunk.chunk_text}"
            )
        previous_chunk = chunk.chunk_text


def test_no_stride_no_overlaps() -> None:
    """This tests for non overlapping chunks at stride 0"""

    document_from_md = (FIXTURE_DATA / "x.md").read_text()

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document_from_md,
        100,
        None,
        0,
        600,
    )
    assert len(chunks) > 1
    previous_chunk = chunks[0].chunk_text
    for chunk in chunks[1:]:
        assert previous_chunk is not None
        assert chunk.chunk_text is not None
        # overlap is only counted as such when its 10 characters
        for i in range(0, len(previous_chunk) - 10):
            if chunk.chunk_text.startswith(previous_chunk[i:]):
                raise ValueError(
                    f"chunks overlapping with {len(previous_chunk[i:])} characters!\n{previous_chunk[i:]}\nthere should be no overlap here\n{chunk.chunk_text[:len(previous_chunk[i:])]}"
                )
        previous_chunk = chunk.chunk_text
