import logging
from multiprocessing import Pool
from multiprocessing.context import TimeoutError
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
    tokenizer: tokenizer_lib.Tokenizer | None,
    stride: int,
    chunking_timout: int,
) -> tuple[core.TextChunk] | None:
    """Iterates over documents to yield text chunks along with the document ID.

    Args:
      documents: A sequence of Document objects.
      max_char_buffer: The maximum character buffer size for the ChunkIterator.
      tokenizer: Optional tokenizer instance.
      stride: Number of characters to overlap the chunks.

    Yields:
      TextChunk containing document ID for a corresponding document.

    Raises:
      InvalidDocumentError: If restrict_repeats is True and the same document ID
        is visited more than once. Valid documents prior to the error will be
        returned.
    """
    try:
        chunks =  core.ChunkIterator(
            document,
            max_char_buffer=max_char_buffer,
            tokenizer_impl=tokenizer or tokenizer_lib.RegexTokenizer(),
            stride=stride,
        )
        with Pool(1) as p:
            return p.apply_async(
                func=tuple,
                args=(chunks,)
            ).get(timeout=chunking_timout)
    except TimeoutError:
        logger.warning(f"skipping {document} due to chunking timeout")
        return None


class ChunkingExtractor:
    """Extractor that chunks extraction and aggregates results per key.
    This extractor calls the base extraction function multiple times
    (for each chunk in the document) on the same input text,
    passing some previous context to each subsequent call.

    TODO: adapt ->
    See UnionExtractor for accepted parameters and details about the aggregation logic.

    Args:
        skip_type_mismatches: If True, skips keys with inconsistent types across extractions
            instead of raising an error (default: False)
        return_as_list: List of field names to return as lists of all extracted values
            (default: None)
        tokenizer: tokenizer to use for chunking
        max_char_buffer: Max chunk size in characters
        stride: Number of characters to overlap chunks
        stride_factor: If provided, overrides stride with a fraction of max_char_buffer (e.g. 0.1 for 10% overlap)
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
        chunking_timout: int = 3600,
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
        self.chunking_timout = chunking_timout

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        current_kwargs = {
            **combined_kwargs,
            "return_messages_formatted": True,
            "truncate_user_message_formatted": None,
        }

        chunks = _document_chunk_iterator(
            args[0],
            self.max_char_buffer,
            self.tokenizer,
            self.stride,
            self.chunking_timout,
        )

        if chunks is None:
            return dict()

        if self.default_kwargs.get("llm", dict()) == dict():
            logging.info(f"{str(len(chunks)).rjust(4, ' ')} chunks in document {args[-1]}")
            return dict()

        results = []
        if self.verbose:
            logger.info(f"starting processing for text {args[-1]}")
            logger.info(args[0])
            # wrapping in tqdm doesn't change the functionality but upsets mypy.
            # hence we need the '# type: ignore' comment
            chunks = tqdm(chunks, desc=args[-1])  # type: ignore
        for i, chunk in enumerate(chunks):

            current_kwargs["text_id"] = f"{args[-1]}_chunk_{i}"
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
