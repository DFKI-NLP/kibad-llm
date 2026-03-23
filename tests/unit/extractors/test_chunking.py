from multiprocessing.context import TimeoutError
from pathlib import Path

import pytest

from kibad_llm.extractors.chunking import _document_chunk_iterator
from kibad_llm.extractors.chunking_utils.core import TextChunk
from tests import FIXTURE_DATA_ROOT

FIXTURE_DATA = FIXTURE_DATA_ROOT / "chunking"


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
            0.00001,
        )


def test_first_token_too_long() -> None:
    """If a token is larger than max_char_buffer, it gets its own chunk."""

    input_text = [
        # token gets its own chunk as it's bigger than max_char_buffer
        "TooBigTokennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",  # 60 chars
        # rest of the "broken" sentence gets its own chunk
        "normal tokens here.",  # 19
        # new complete sentence gets its own chunk because the next sentence wouldn't
        # fit into max_char_buffer
        "some more.",  # 10
        # start of sentence gets its own chunk, because the total sentence is too big
        "more normal tokens",  # 18 chars
        # token gets its own chunk as it's bigger than max_char_buffer,
        # even within sentences
        "tooBigTokennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",  # 60 chars
        # rest of the "broken" sentence gets its own chunk
        "and normal end.",  # 15 chars
        # start of sentence gets its own chunk, because the total sentence is too big
        "normal start here",
        "tooBigTokennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn",  # 60 chars
        ".",  # 1 char
        "normal sentence here. the end.",  # 30 chars
    ]
    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        " ".join(input_text),
        50,
        None,
        10,
    )
    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == input_text


def test_chunk_case_a() -> None:
    """
    A)
    If a sentence length exceeds the max char buffer, then it needs to be broken
    into chunks that can fit within the max char buffer. We do this in a way that
    maximizes the chunk length while respecting newlines (if present) and token
    boundaries.
    Consider this sentence from a poem by John Donne:
    ```
    No man is an island,
    Entire of itself,
    Every man is a piece of the continent,
    A part of the main.
    ```
    With max_char_buffer=40, the chunks are:
    * "No man is an island,\nEntire of itself," len=38
    * "Every man is a piece of the continent," len=38
    * "A part of the main." len=19

    """

    input_text = "No man is an island,\nEntire of itself,\nEvery man is a piece of the continent,\nA part of the main."
    expected_chunks = [
        "No man is an island,\nEntire of itself,",  # len=38
        "Every man is a piece of the continent,",  # len=38
        "A part of the main.",  # len=19
    ]

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        input_text,
        40,
        None,
        10,
    )

    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == expected_chunks


def test_chunk_case_b() -> None:
    """
    B)
    If a single token exceeds the max char buffer, it comprises the whole chunk.
    Consider the sentence:
    "This is antidisestablishmentarianism."
    With max_char_buffer=20, the chunks are:
    * "This is" len=7
    * "antidisestablishmentarianism" len=28
    * "." len(1)
    """

    input_text = "This is antidisestablishmentarianism."

    expected_chunks = [
        "This is",  # len=7
        "antidisestablishmentarianism",  # len=28
        ".",  # len(1)
    ]

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        input_text,
        20,
        None,
        10,
    )

    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == expected_chunks


def test_chunk_case_c() -> None:
    """
    C)
    If multiple *whole* sentences can fit within the max char buffer, then they
    are used to form the chunk.
    Consider the sentences:
    "Roses are red. Violets are blue. Flowers are nice. And so are you."
    With max_char_buffer=60, the chunks are:
    * "Roses are red. Violets are blue. Flowers are nice." len=50
    * "And so are you." len=15
    """

    input_text = "Roses are red. Violets are blue. Flowers are nice. And so are you."

    expected_chunks = [
        "Roses are red. Violets are blue. Flowers are nice.",  # len=50
        "And so are you.",  # len=15
    ]

    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        input_text,
        60,
        None,
        10,
    )

    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == expected_chunks
