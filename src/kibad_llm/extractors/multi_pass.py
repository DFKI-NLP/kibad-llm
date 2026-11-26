"""[`MultiPassExtractorWithChunking`][.MultiPassExtractorWithChunking] chunking based extraction in multiple passes.

Classes:
    MultiPassExtractorWithChunking: Combines [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] and
        [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] by running one pass per
        override and, within each pass, the ChunkingExtractor loop over the chunks of the text.
"""

import json
from typing import Any

from llama_index.core.base.llms.types import MessageRole

from kibad_llm.llms.request import (
    SYSTEM_MESSAGE_KEY,
    USER_MESSAGE_KEY,
    SimpleChatMessage,
)

from .aggregation_utils import Aggregator
from .base import extract_from_text_lenient, prepare_request
from .chunking import _document_chunk_iterator
from .chunking_utils import tokenizers as tokenizer_lib


class MultiPassExtractorWithChunking:
    """Extractor that executes one extraction pass for each entry in a list (or dict) of parameter overrides.
    In each pass, the input text is chunked and the base extraction function is called on each chunk.
    The results of the chunks are aggregated per pass, and then the results of all passes are aggregated
    into a single result.

    Attributes:
        overrides: A list of dictionaries containing parameter overrides for each extraction pass.
            The number of entries defines the number of passes. Can also be a dictionary in
            the format {"pass id" -> "override parameters"} to improve config readability
            (the pass id is not used for anything else).
        aggregator: Aggregator function to combine the results of the passes (outer loop).
        chunking_aggregator: Aggregator function to combine the results of the chunks within a single
            pass (inner loop).
        return_as_list: List of field names to return as lists of all extracted values.
            Length will be the number of extraction passes (override entries x chunks).
        tokenizer: Tokenizer to use for chunking.
        max_char_buffer: Max chunk size in characters.
        default_kwargs: Additional keyword arguments passed to the base extraction function.

    Warning:
        If a Token that is greater than max_char_buffer is encountered, it becomes its own chunk.
        This edge case can produce chunks that are larger than max_char_buffer would allow.

    See [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] as well as
    [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] for accepted parameters
    and details about the aggregation logic.
    """

    def __init__(
        self,
        overrides: list[dict] | dict[str, dict],
        aggregator: Aggregator,
        chunking_aggregator: Aggregator,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        with_history: bool = False,
        **kwargs,
    ):
        """Assign args to attributes with safety checks and conversions

        Args:
            overrides: A list of dictionaries containing parameter overrides for each extraction pass.
                Can also be a dictionary in the format {"pass id" -> "override parameters"} to improve
                config readability (the pass id is not used for anything else).
            aggregator: Aggregator function to use across passes (outer loop).
            chunking_aggregator: Aggregator function to use across chunks (inner loop).
            return_as_list: List of field names to return as lists of all extracted values
            tokenizer: Tokenizer to use for chunking.
            max_char_buffer: Max chunk size in characters.

        Keyword Args:
            **kwargs (Any): Default keyword arguments forwarded to the base extraction function.

        Raises:
            ValueError: If no overrides are supplied, there can't be an extraction.
        """
        if len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters")
        if isinstance(overrides, list):
            overrides = {str(i): override for i, override in enumerate(overrides)}
        self.overrides = overrides
        self.aggregator = aggregator
        self.chunking_aggregator = chunking_aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer
        self.with_history = with_history

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        """Process singular text in chunks with multiple passes.

        Args:
            *args (Any): Positional form of `text` and `text_id`, in that order.

        Returns:
            Dict with the key `structured` that holds the aggregated structured outputs.
            Additionally, there can be lists for fields at the keys `"{field}_list"`. These hold
            one entry per extraction call, i.e. one per (pass, chunk) pair in pass-major
            order: all chunks of the first pass, then all chunks of the second, and so on.
            This flattens the per-call layout of
            [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] on the outside and
            [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] on the inside.

        Keyword Args:
            text (str): Input document to process.
            text_id (str): Id of input document.
            **kwargs (Any): Additional keyword arguments for
                [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient].
        """

        # extract text and id in most compatible way
        text = kwargs.pop("text", None)
        if text is None:
            text = args[0]

        text_id = kwargs.pop("text_id", None)
        if text_id is None:
            text_id = args[-1]

        combined_kwargs = {**self.default_kwargs, **kwargs}

        # chunk the input text first so that we don't have to do it for every pass
        chunks = _document_chunk_iterator(
            document=text,
            max_char_buffer=self.max_char_buffer,
            tokenizer=self.tokenizer,
        )

        # the raw results of every single extraction call (one per chunk and pass)
        # to build the "{field}_list" entries from
        all_results = []

        history: list[SimpleChatMessage] = []
        # aggregated structured output per pass
        all_passes_results = []
        for override_name, override_params in self.overrides.items():
            current_pass_results = []
            current_pass_kwargs = {**combined_kwargs, **override_params}
            for i, chunk in enumerate(chunks):
                if self.with_history:

                    # some kind of from current_pass_kwargs
                    prompt_template = current_pass_kwargs["prompt_template"].copy()
                    prompt_template[USER_MESSAGE_KEY] = None

                    llm = current_pass_kwargs["llm"]
                    request_preparer = prepare_request if llm is None else llm.prepare_request
                    request = request_preparer(
                        prompt_template,
                        document=text[
                            chunk.char_interval.start_pos or 0 : chunk.char_interval.end_pos
                        ],
                        schema=None,
                        history=(),
                    )

                    system_message = request.current_messages[0]
                    if (
                        system_message.role is not MessageRole.SYSTEM
                    ):  # TODO: test whether is not or !=
                        raise ValueError(
                            "Retrieved incorrect message from prepare_request. system_message expected."
                        )

                    current_pass_kwargs["history"] = [system_message] + history
                    current_pass_kwargs["prompt_template"][SYSTEM_MESSAGE_KEY] = None
                    current_pass_kwargs["return_messages_formatted"] = True
                    current_pass_kwargs["truncate_user_message_formatted"] = None

                # for each override, run the ChunkingExtractor loop over all chunks of the text
                current_chunk_result = extract_from_text_lenient(
                    text=text,
                    text_id=f"{text_id}_{override_name}_chunk_{i}",
                    **current_pass_kwargs,
                    # This may raise an error if character_start or character_end is already provided via kwargs,
                    # but we want to be strict about not allowing that since it would interfere with the chunking logic.
                    character_start=chunk.char_interval.start_pos or 0,
                    character_end=chunk.char_interval.end_pos,
                )

                current_pass_results.append(current_chunk_result)

            all_results.extend(current_pass_results)

            # aggregate the results of the current override's extraction passes over all chunks
            current_pass_structured_outputs = [
                v.get("structured", None) for v in current_pass_results
            ]
            aggregated_pass_result = self.chunking_aggregator(current_pass_structured_outputs)
            all_passes_results.append(aggregated_pass_result)
            if self.with_history:
                if len(current_pass_results) == 0:
                    raise ValueError("No results returned by ASSISTANT.")
                messages_formatted = current_pass_results[0]["messages_formatted"]
                # TODO: should use a constant for MessageRole
                user_message_key = MessageRole.USER.name.lower()
                if len(messages_formatted) != 1 or user_message_key not in messages_formatted:
                    raise ValueError("Expecting exactly one user message.")
                user_message_content = messages_formatted[user_message_key]
                history.append(
                    SimpleChatMessage(role=MessageRole.USER, content=user_message_content)
                )
                history.append(
                    SimpleChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=json.dumps(aggregated_pass_result, ensure_ascii=False),
                    )
                )

        # aggregate the previously aggregated results, but now across the overrides, to get a single result.
        aggregated_structured = self.aggregator(all_passes_results)

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in all_results]
        return result
