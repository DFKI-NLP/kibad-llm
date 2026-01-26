from collections.abc import Iterable, Iterator
from typing import Any

from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from llama_index.core.base.llms.types import MessageRole

from kibad_llm.llms.base import SimpleChatMessage

from .base import extract_from_text_lenient
from .chunking_helpers import core
from .chunking_helpers import tokenizers as tokenizer_lib
from .union import UnionExtractor, _aggregate_structured_outputs_union


def _document_chunk_iterator(
    document: str,
    max_char_buffer: int,
    tokenizer: tokenizer_lib.Tokenizer | None,
) -> Iterator[core.TextChunk]:
    """Iterates over documents to yield text chunks along with the document ID.

    Args:
      documents: A sequence of Document objects.
      max_char_buffer: The maximum character buffer size for the ChunkIterator.
      tokenizer: Optional tokenizer instance.

    Yields:
      TextChunk containing document ID for a corresponding document.

    Raises:
      InvalidDocumentError: If restrict_repeats is True and the same document ID
        is visited more than once. Valid documents prior to the error will be
        returned.
    """
    yield from core.ChunkIterator(
        document,
        max_char_buffer=max_char_buffer,
        tokenizer_impl=tokenizer or tokenizer_lib.RegexTokenizer(),
    )


class ChunkingExtractor(UnionExtractor):
    """Extractor that chunks extraction and aggregates results per key.
    This extractor calls the base extraction function multiple times
    (for each chunk in the document) on the same input text,
    passing some previous context to each subsequent call.

    TODO: adapt ->
    See UnionExtractor for accepted parameters and details about the aggregation logic.
    """

    def __init__(
        self,
        overrides: list[dict],
        skip_type_mismatches: bool = False,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 10000,
        **kwargs,
    ):
        if len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters")
        self.overrides = overrides
        self.skip_type_mismatches = skip_type_mismatches
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        current_kwargs = {
            **combined_kwargs,
            "return_messages_formatted": True,
            "truncate_user_message_formatted": None,
        }

        chunks = _document_chunk_iterator(args[0], self.max_char_buffer, self.tokenizer)
        previous_document_chunk = "Noch kein Kontext vorhanden."
        results = []
        for i, chunk in enumerate(chunks):
            current_kwargs["text_id"] = f"{args[-1]}_chunk_{i}"
            current_result = extract_from_text_lenient(
                text=chunk.chunk_text,
                previous_document_chunk=previous_document_chunk,
                **current_kwargs,
            )
            results.append(current_result)
            previous_document_chunk = chunk.chunk_text

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = _aggregate_structured_outputs_union(
            structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        )

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result
