"""
These tests take care of the chunking extractor as well as the chunking_utils
that are used by it.
"""

import json
from multiprocessing.context import TimeoutError
from pathlib import Path
import textwrap
from typing import TypedDict

import pytest

from kibad_llm.extractors.chunking import (
    _document_chunk_iterator,
)
from kibad_llm.extractors.chunking_utils.core import (
    ChunkIterator,
    TextChunk,
    get_token_interval_text,
)
from kibad_llm.extractors.chunking_utils.tokenizers import (
    RegexTokenizer,
    TokenInterval,
)
from tests import FIXTURE_DATA_ROOT

FIXTURE_DATA = FIXTURE_DATA_ROOT / "chunking"


def test_full_document() -> None:
    class document_dict(TypedDict):
        text: str
        chunk_texts: list[str]

    document: document_dict = json.loads(
        Path(FIXTURE_DATA).joinpath("25ABQZIH.pdf.json").read_text()
    )
    chunks: tuple[TextChunk, ...] = _document_chunk_iterator(
        document["text"],
        20000,
        None,
    )
    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == document["chunk_texts"]


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
    )

    chunk_texts = [chunk.chunk_text for chunk in chunks]
    assert chunk_texts == expected_chunks


#
#
# The following test cases have been copied and adopted from googles langextract!
#
#


def test_multi_sentence_chunk():
    text = "This is a sentence. This is a longer sentence. Mr. Bond\nasks\nwhy?"
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=50,
        tokenizer_impl=RegexTokenizer(),
    )
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=0, end_index=11) == chunk_interval
    assert (
        get_token_interval_text(tokenized_text, chunk_interval)
        == "This is a sentence. This is a longer sentence."
    )
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=11, end_index=17) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "Mr. Bond\nasks\nwhy?"
    with pytest.raises(StopIteration):
        next(chunk_iter)


def test_sentence_with_multiple_newlines_and_right_interval():
    text = "This is a sentence\n\n" + "This is a longer sentence\n\n" + "Mr\n\nBond\n\nasks why?"
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_interval = TokenInterval(start_index=0, end_index=len(tokenized_text.tokens))
    assert get_token_interval_text(tokenized_text, chunk_interval) == text


def test_break_sentence():
    text = "This is a sentence. This is a longer sentence. Mr. Bond\nasks\nwhy?"
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=12,
        tokenizer_impl=RegexTokenizer(),
    )
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=0, end_index=3) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "This is a"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=3, end_index=5) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "sentence."
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=5, end_index=8) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "This is a"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=8, end_index=9) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "longer"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=9, end_index=11) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "sentence."
    for _ in range(2):
        next(chunk_iter)
    with pytest.raises(StopIteration):
        next(chunk_iter)


# ===================================================================


def test_long_token_gets_own_chunk():
    text = "This is a sentence. This is a longer sentence. Mr. Bond\nasks\nwhy?"
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=7,
        tokenizer_impl=RegexTokenizer(),
    )
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=0, end_index=2) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "This is"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=2, end_index=3) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "a"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=3, end_index=4) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "sentence"
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=4, end_index=5) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == "."
    for _ in range(9):
        next(chunk_iter)
    with pytest.raises(StopIteration):
        next(chunk_iter)


def test_newline_at_chunk_boundary_does_not_create_empty_interval():
    """Test that newlines at chunk boundaries don't create empty token intervals.

    When a newline occurs exactly at a chunk boundary, the chunking algorithm
    should not attempt to create an empty interval (where start_index == end_index).
    This was causing a ValueError in create_token_interval().
    """
    text = "First sentence.\nSecond sentence that is longer.\nThird sentence."
    tokenized_text = RegexTokenizer().tokenize(text)

    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=20,
        tokenizer_impl=RegexTokenizer(),
    )
    chunks = list(chunk_iter)

    for chunk in chunks:
        assert (
            chunk.token_interval.start_index < chunk.token_interval.end_index
        ), "Chunk should have non-empty interval"

    expected_intervals = [(0, 3), (3, 6), (6, 9), (9, 12)]
    actual_intervals = [
        (chunk.token_interval.start_index, chunk.token_interval.end_index) for chunk in chunks
    ]
    assert actual_intervals == expected_intervals


def test_chunk_unicode_text():
    text = textwrap.dedent(
        """\
    Chief Complaint:
    ‘swelling of tongue and difficulty breathing and swallowing’
    History of Present Illness:
    77 y o woman in NAD with a h/o CAD, DM2, asthma and HTN on altace."""
    )
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=200,
        tokenizer_impl=RegexTokenizer(),
    )
    chunk_interval = next(chunk_iter).token_interval
    assert TokenInterval(start_index=0, end_index=len(tokenized_text.tokens)) == chunk_interval
    assert get_token_interval_text(tokenized_text, chunk_interval) == text


def test_newlines_is_secondary_sentence_break():
    text = textwrap.dedent(
        """\
    Medications:
    Theophyline (Uniphyl) 600 mg qhs – bronchodilator by increasing cAMP used
    for treating asthma
    Diltiazem 300 mg qhs – Ca channel blocker used to control hypertension
    Simvistatin (Zocor) 20 mg qhs- HMGCo Reductase inhibitor for
    hypercholesterolemia
    Ramipril (Altace) 10 mg BID – ACEI for hypertension and diabetes for
    renal protective effect"""
    )
    tokenized_text = RegexTokenizer().tokenize(text)
    chunk_iter = ChunkIterator(
        text,
        max_char_buffer=200,
        tokenizer_impl=RegexTokenizer(),
    )

    first_chunk = next(chunk_iter)
    expected_first_chunk_text = textwrap.dedent(
        """\
    Medications:
    Theophyline (Uniphyl) 600 mg qhs – bronchodilator by increasing cAMP used
    for treating asthma
    Diltiazem 300 mg qhs – Ca channel blocker used to control hypertension"""
    )
    assert (
        get_token_interval_text(tokenized_text, first_chunk.token_interval)
        == expected_first_chunk_text
    )

    assert first_chunk.token_interval.end_index > first_chunk.token_interval.start_index

    second_chunk = next(chunk_iter)
    expected_second_chunk_text = textwrap.dedent(
        """\
    Simvistatin (Zocor) 20 mg qhs- HMGCo Reductase inhibitor for
    hypercholesterolemia
    Ramipril (Altace) 10 mg BID – ACEI for hypertension and diabetes for
    renal protective effect"""
    )
    assert (
        get_token_interval_text(tokenized_text, second_chunk.token_interval)
        == expected_second_chunk_text
    )
    with pytest.raises(StopIteration):
        next(chunk_iter)
