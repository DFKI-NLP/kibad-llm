"""[`MultiPassExtractorWithChunking`][.MultiPassExtractorWithChunking] chunking based extraction in multiple passes.

Classes:
    MultiPassExtractorWithChunking: Combines [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] and
        [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] by running one pass per
        override and, within each pass, the ChunkingExtractor loop over the chunks of the text.
"""

from typing import Any

from .aggregation_utils import Aggregator
from .base import extract_from_text_lenient
from .chunking import _document_chunk_iterator
from .chunking_utils import tokenizers as tokenizer_lib


class MultiPassExtractorWithChunking:
    """Extractor that repeats extraction for a list of overrides over chunked text and aggregates results per key
    This extractor chunks the incoming text and then, for each override, extracts from all chunks.
    First it aggregates across the chunks for each override, to create one result per override.
    Then it aggregates those results into one.

    Attributes:
        overrides: A list of dictionaries containing parameter overrides for each extraction.
        override_aggregator: Aggregator function to combine the results of the overrides (outer loop).
        chunking_aggregator: Aggregator function to combine the results of the chunks of a single
            override (inner loop).
        return_as_list: List of field names to return as lists of all extracted values.
            Length will be the number of extraction passes (override entries x chunks).
        tokenizer: Tokenizer to use for chunking.
        max_char_buffer: Max chunk size in characters.
        default_kwargs: Additional keyword arguments passed to the base extraction function.

    Warning:
        If a Token that is greater than max_char_buffer is encountered, it becomes its own chunk.
        This edge case can produce chunks that are larger than max_char_buffer would allow.

    See [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] as well as [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] for accepted parameters and details about the aggregation logic.
    """

    def __init__(
        self,
        overrides: list[dict] | dict[str, dict],
        override_aggregator: Aggregator,
        chunking_aggregator: Aggregator,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        **kwargs,
    ):
        """Assign args to attributes with safety checks and conversions

        Args:
            overrides: A list of dictionaries containing parameter overrides for each extraction.
            override_aggregator: Aggregator function to use across overrides (outer loop).
            chunking_aggregator: Aggregator function to use across chunks (inner loop).
            return_as_list: List of field names to return as lists of all extracted values
            tokenizer: Tokenizer to use for chunking.
            max_char_buffer: Max chunk size in characters.

        Keyword Args:
            *: Additional keyword arguments passed to the base extraction function.

        Raises:
            ValueError: If no overrides are supplied, there can't be an extraction.
        """
        if len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters")
        if isinstance(overrides, list):
            overrides = {str(i): override for i, override in enumerate(overrides)}
        self.overrides = overrides
        self.override_aggregator = override_aggregator
        self.chunking_aggregator = chunking_aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        """Process singular text in chunks with multiple passes.

        Args:
            *args (Any): Positional form of `text` and `text_id`, in that order.


        Keyword Args:
            text (str): Input document to process.
            text_id (str): Id of input document.
            * (Any): Refer to [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient]

        Returns:
            Dict with the key `structured` that holds the aggregated structured outputs.
            Additionally there can be lists for fields at the keys `"{field}_list"`. These hold
            one entry per extraction call, i.e. one per (override, chunk) pair in override-major
            order: all chunks of the first override, then all chunks of the second, and so on.
            This flattens the per-call layout of
            [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] on the outside and
            [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] on the inside.
        """

        # extract text and id in most compatible way
        text = kwargs.pop("text", None)
        if text is None:
            text = args[0]

        text_id = kwargs.pop("text_id", None)
        if text_id is None:
            text_id = args[-1]

        combined_kwargs = {**self.default_kwargs, **kwargs}

        # chunk the input text first so that we don't have to do it for every override
        chunks = _document_chunk_iterator(
            document=text,
            max_char_buffer=self.max_char_buffer,
            tokenizer=self.tokenizer,
        )

        # aggregated structured output per override, and the raw results of every single extraction
        # call (one per chunk and override) to build the "{field}_list" entries from
        override_structured = []
        all_results = []
        for override_name, override_params in self.overrides.items():
            override_results = []
            current_kwargs = {**combined_kwargs, **override_params}
            for i, chunk in enumerate(chunks):
                # for each override, run the ChunkingExtractor loop over all chunks of the text
                current_result = extract_from_text_lenient(
                    text=text,
                    text_id=f"{text_id}_{override_name}_chunk_{i}",
                    **current_kwargs,
                    # This may raise an error if character_start or character_end is already provided via kwargs,
                    # but we want to be strict about not allowing that since it would interfere with the chunking logic.
                    character_start=chunk.char_interval.start_pos or 0,
                    character_end=chunk.char_interval.end_pos,
                )

                override_results.append(current_result)

            all_results.extend(override_results)

            # aggregate the results of the current override's extraction passes over all chunks
            override_structured_outputs = [v.get("structured", None) for v in override_results]
            override_structured.append(self.chunking_aggregator(override_structured_outputs))

        # aggregate the previously aggregated results, but now across the overrides, to get a single result.
        aggregated_structured = self.override_aggregator(override_structured)

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in all_results]
        return result
