import logging
from typing import Any

from tqdm import tqdm

from .aggregation_utils import Aggregator
from .base import extract_from_text_lenient
from .chunking_utils import core
from .chunking_utils import tokenizers as tokenizer_lib

logger = logging.getLogger(__name__)


def _document_chunk_iterator(
    document: str,
    max_char_buffer: int,
    tokenizer: tokenizer_lib.Tokenizer | None = None,
) -> tuple[core.TextChunk, ...]:
    """Iterates over documents to return text chunks along with the document ID.

    Args:
        document: A sequence of Document objects.
        max_char_buffer: The maximum character buffer size for the ChunkIterator.
        tokenizer: Optional tokenizer instance.

    Returns:
        TextChunk containing document ID for a corresponding document.

    Raises:
        InvalidDocumentError: If restrict_repeats is True and the same document ID
            is visited more than once. Valid documents prior to the error will be
            returned.
    """
    return tuple(
        core.ChunkIterator(
            document,
            max_char_buffer=max_char_buffer,
            tokenizer_impl=tokenizer or tokenizer_lib.RegexTokenizer(),
        )
    )


class ChunkingExtractor:
    """Extractor that chunks extraction and aggregates results per key.
    This extractor calls the base extraction function multiple times
    (for each chunk in the document) on the same input text,
    passing some previous context to each subsequent call.

    Pass llm=None with verbose=True to get the number of chunks per document without inference.

    WARNING:
    If a Token that is greater than max_char_buffer is encountered, it becomes its own chunk.
    This edge case can produce chunks that are larger than max_char_buffer would allow.

    Args:
        aggregator: Method to aggregate the llm output for the individual chunks before returning
        return_as_list: List of field names to return as lists of all extracted values
        tokenizer: tokenizer to use for chunking
        max_char_buffer: Max chunk size in characters
        verbose: Adds verbose logging
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        aggregator: Aggregator,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        verbose: bool = False,
        **kwargs,
    ):
        self.aggregator = aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer
        self.verbose = verbose

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        text = kwargs.pop("text", None)
        if text is None:
            text = args[0]

        text_id = kwargs.pop("text_id", None)
        if text_id is None:
            text_id = args[-1]

        combined_kwargs = {**self.default_kwargs, **kwargs}

        chunks = _document_chunk_iterator(
            document=text,
            max_char_buffer=self.max_char_buffer,
            tokenizer=self.tokenizer,
        )

        results = []
        if self.verbose:
            logger.info(f"starting processing for text {text_id}")
            logger.info(f"{text[:100]}[...]{text[100:]}" if len(text) > 200 else text)
            logging.info(f"{str(len(chunks)).rjust(4, ' ')} chunks in document {args[-1]}")
            # wrapping in tqdm doesn't change the functionality but upsets mypy.
            # hence we need the '# type: ignore' comment
            chunks = tqdm(chunks, desc=text_id)  # type: ignore
        for i, chunk in enumerate(chunks):
            current_result = extract_from_text_lenient(
                text=text,
                text_id=f"{text_id}_chunk_{i}",
                **combined_kwargs,
                # This may raise an error if character_start or character_end is already provided via kwargs,
                # but we want to be strict about not allowing that since it would interfere with the chunking logic.
                character_start=chunk.char_interval.start_pos or 0,
                character_end=chunk.char_interval.end_pos,
            )
            results.append(current_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = self.aggregator(structured_outputs)

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
