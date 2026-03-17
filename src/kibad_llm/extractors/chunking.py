import logging
from multiprocessing import Pool
from multiprocessing.context import TimeoutError
from typing import Any

from tqdm import tqdm

from .aggregation_utils import Aggregator
from .base import (
    SingleExtractionResult,
    exception2error_msg,
    extract_from_text_lenient,
)
from .chunking_utils import core
from .chunking_utils import tokenizers as tokenizer_lib

logger = logging.getLogger(__name__)


def _document_chunk_iterator(
    document: str,
    max_char_buffer: int,
    tokenizer: tokenizer_lib.Tokenizer | None,
    stride: int,
    chunking_timeout: float,
) -> tuple[core.TextChunk, ...]:
    """Iterates over documents to return text chunks along with the document ID.

    Args:
        documents: A sequence of Document objects.
        max_char_buffer: The maximum character buffer size for the ChunkIterator.
        tokenizer: Optional tokenizer instance.
        stride: Number of characters to overlap the chunks.
        chunking_timeout: Number of seconds after which to raise the TimeoutError.

    Returns:
        TextChunk containing document ID for a corresponding document.

    Raises:
        TimeoutError: If the chunks cannot be returned within the timeout,
            a TimeoutError is raised
        InvalidDocumentError: If restrict_repeats is True and the same document ID
            is visited more than once. Valid documents prior to the error will be
            returned.
    """
    chunks = core.ChunkIterator(
        document,
        max_char_buffer=max_char_buffer,
        tokenizer_impl=tokenizer or tokenizer_lib.RegexTokenizer(),
        stride=stride,
    )
    with Pool(1) as p:
        return p.apply_async(func=tuple, args=(chunks,)).get(timeout=chunking_timeout)


class ChunkingExtractor:
    """Extractor that chunks extraction and aggregates results per key.
    This extractor calls the base extraction function multiple times
    (for each chunk in the document) on the same input text,
    passing some previous context to each subsequent call.

    Pass llm=None to get the number of chunks per document without inference.

    Args:
        aggregator: Method to aggregate the llm output for the individual chunks before returning
        return_as_list: List of field names to return as lists of all extracted values
        tokenizer: tokenizer to use for chunking
        max_char_buffer: Max chunk size in characters
        stride: Number of characters to overlap chunks
        stride_factor: If provided, overrides stride with a fraction of max_char_buffer (e.g. 0.1 for 10% overlap)
        verbose: Adds verbose logging
        chunking_timeout: Time after which chunking is cancelled because of gibberish input
        **kwargs: Additional keyword arguments passed to the base extraction function.
    """

    def __init__(
        self,
        aggregator: Aggregator,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        stride: int = 1000,
        stride_factor: float | None = None,
        verbose: bool = False,
        chunking_timeout: int = 3600,
        **kwargs,
    ):
        self.aggregator = aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer
        if stride_factor is not None:
            self.stride = int(max_char_buffer * stride_factor)
        else:
            self.stride = stride
        self.verbose = verbose
        self.chunking_timeout = chunking_timeout

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        text = kwargs.pop("text", None)
        if text is None:
            text = args[0]

        text_id = kwargs.pop("text_id", None)
        if text_id is None:
            text_id = args[-1]

        combined_kwargs = {**self.default_kwargs, **kwargs}
        current_kwargs = {
            **combined_kwargs,
            "return_messages_formatted": True,
            "truncate_user_message_formatted": None,
        }

        try:
            chunks = _document_chunk_iterator(
                text,
                self.max_char_buffer,
                self.tokenizer,
                self.stride,
                self.chunking_timeout,
            )
        except TimeoutError as e:
            logger.error(f"document {text_id} timed out during chunking")
            out = SingleExtractionResult()
            error_msg_short, error_msg_long = exception2error_msg(e)
            out["errors"].append(error_msg_short)
            out["errors_long"].append(error_msg_long)

            err_result: dict[str, Any] = {
                "structured": out.structured,
            }
            for field in self.return_as_list:
                err_result[f"{field}_list"] = [out.get(field, None)]
            return err_result

        if self.default_kwargs.get("llm", dict()) == dict():
            logging.info(f"{str(len(chunks)).rjust(4, ' ')} chunks in document {args[-1]}")
            out = SingleExtractionResult()
            empty_result: dict[str, Any] = {
                "structured": out.structured,
            }
            for field in self.return_as_list:
                empty_result[f"{field}_list"] = [out.get(field, None)]
            return empty_result

        results = []
        if self.verbose:
            logger.info(f"starting processing for text {text_id}")
            logger.info(f"{text[:100]}[...]{text[100:]}" if len(text) > 200 else text)
            # wrapping in tqdm doesn't change the functionality but upsets mypy.
            # hence we need the '# type: ignore' comment
            chunks = tqdm(chunks, desc=text_id)  # type: ignore
        for i, chunk in enumerate(chunks):

            current_kwargs["text_id"] = f"{text_id}_chunk_{i}"
            current_kwargs.update(
                {
                    "augment_metadata_kwargs": {
                        "evidence_character_offset": chunk.char_interval.start_pos
                    }
                }
            )
            current_result = extract_from_text_lenient(
                text=chunk.chunk_text,
                **current_kwargs,
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
