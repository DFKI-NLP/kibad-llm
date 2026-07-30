"""[`ConditionalUnionChunkingExtractor`][.ConditionalUnionChunkingExtractor] for multi-pass extraction
on text chunks, with chat history passed between passes.

Classes:
    ConditionalUnionChunkingExtractor: Extends [`ConditionalUnionExtractor`][kibad_llm.extractors.conditional.ConditionalUnionExtractor]
        by chunking the text before feeding it into the extractor.
"""

from typing import Any

from llama_index.core.base.llms.types import MessageRole

from kibad_llm.llms.base import SimpleChatMessage

from .aggregation_utils import Aggregator
from .base import extract_from_text_lenient
from .chunking_utils import core
from .chunking_utils import tokenizers as tokenizer_lib
from .conditional import ConditionalUnionExtractor


def _document_chunk_iterator(
    document: str,
    max_char_buffer: int,
    tokenizer: tokenizer_lib.Tokenizer | None = None,
) -> tuple[core.TextChunk, ...]:
    """Iterates over a document to return it in text chunks

    Args:
        document: An input text as str.
        max_char_buffer: The maximum character buffer size for the ChunkIterator.
        tokenizer: Optional tokenizer instance.

    Returns:
        Tuple of TextChunks.
    """
    return tuple(
        core.ChunkIterator(
            document,
            max_char_buffer=max_char_buffer,
            tokenizer_impl=tokenizer or tokenizer_lib.RegexTokenizer(),
        )
    )


class ConditionalUnionChunkingExtractor(ConditionalUnionExtractor):
    """Extractor that repeats extraction multiple times on text chunks, with history and aggregates results per key.
    This extractor calls the base extraction function multiple times (for each entry in overrides)
    on the same input chunk, for each chunk in the input text, passing the history of previous messages (of a given chunk)
    to each subsequent call.

    See ConditionalUnionExtractor as well as ChunkingExtractor for accepted parameters and details about the aggregation logic.
    """

    def __init__(
        self,
        overrides: list[dict] | dict[str, dict],
        chunking_aggregator: Aggregator,
        union_aggregator: Aggregator,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        **kwargs,
    ):
        if len(overrides) < 1:
            raise ValueError("overrides must contain at least one set of parameters")
        if isinstance(overrides, list):
            overrides = {str(i): override for i, override in enumerate(overrides)}
        self.overrides = overrides
        self.chunking_aggregator = chunking_aggregator
        self.union_aggregator = union_aggregator
        self.return_as_list = return_as_list or []
        self.default_kwargs = kwargs
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        """Process singular text in multiple passes with chat history.

        Args:
            *args (Any): Are forwarded unchanged:
                [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient]

        Keyword Args:
            * (Any): Refer to [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient]

        Returns:
            Dict with the key `structured` that holds the aggregated structured outputs.
            Additionally there can be lists for fields at the keys `"{field}_list"`.
        """

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
        for i, chunk in enumerate(chunks):
            combined_kwargs = {**self.default_kwargs, **kwargs}
            chunk_results = []
            history: list[SimpleChatMessage] = []
            for override_name, override_params in self.overrides.items():
                # adjust kwargs:
                # 1) to return formatted messages for history
                current_kwargs = {
                    **combined_kwargs,
                    **override_params,
                    "return_messages_formatted": True,
                    "truncate_user_message_formatted": None,
                }
                # 2) if history exists, pass it and disable system message
                if len(history) > 0:
                    current_kwargs["prompt_template"]["system_message"] = None
                    current_kwargs["history"] = history

                current_result = extract_from_text_lenient(
                    text=text,
                    text_id=f"{text_id}_chunk_{i}",
                    **current_kwargs,
                    # This may raise an error if character_start or character_end is already provided via kwargs,
                    # but we want to be strict about not allowing that since it would interfere with the chunking logic.
                    character_start=chunk.char_interval.start_pos or 0,
                    character_end=chunk.char_interval.end_pos,
                )

                # collect messages for history
                for role_str, content in current_result["messages_formatted"].items():
                    role = MessageRole(role_str)
                    history.append(SimpleChatMessage(role=role, content=content))
                # append assistant response or error to history
                history.append(
                    SimpleChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=current_result["response_content"] or current_result["error"],
                    )
                )

                chunk_results.append(current_result)

            chunk_structured_outputs = [v.get("structured", None) for v in chunk_results]
            chunk_aggregated_structured = self.union_aggregator(chunk_structured_outputs)

            chunk_result: dict[str, Any] = {
                "structured": chunk_aggregated_structured,
            }
            for field in self.return_as_list:
                chunk_result[f"{field}_list"] = [v.get(field, None) for v in chunk_results]
            results.append(chunk_result)

        structured_outputs = [v.get("structured", None) for v in results]
        aggregated_structured = self.aggregator(structured_outputs)

        result: dict[str, Any] = {
            "structured": aggregated_structured,
        }
        for field in self.return_as_list:
            result[f"{field}_list"] = [v.get(field, None) for v in results]
        return result

