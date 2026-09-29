"""Simple wrapper around OpenAI-like LLMs to indicate vLLM usage in
[`extract_from_text`][kibad_llm.extractors.base.extract_from_text].

Classes:
    OpenAILikeVllm: Simple wrapper around OpenAI-like LLMs to indicate vLLM usage in
        [`extract_from_text`][kibad_llm.extractors.base.extract_from_text].

"""

from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.llms.openai_like import OpenAILike
from openai import BadRequestError

from kibad_llm.llms.base import (
    LLM,
    EmptyReasoningError,
    ReasoningExtractionError,
    SimpleChatMessage,
)
from kibad_llm.utils.log import warn_once


class OpenAILikeVllm(LLM):
    """Simple wrapper around OpenAI-like LLMs to indicate vLLM usage in
    [`extract_from_text`][kibad_llm.extractors.base.extract_from_text].

    Attributes:
        model: Underlying llama-index [`OpenAILike`][llama_index.llms.openai_like.OpenAILike].

    Methods:
        call_llm_chat_with_guided_decoding: Call an OpenAILike chat LLM with optional json schema for guided decoding.
        get_reasoning_from_chat_response: Extract reasoning from a chat response.
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the underlying OpenAILike client.

        Args:
            *args (Any): Forward everything to
                [`OpenAILike`][llama_index.llms.openai_like.OpenAILike].
            **kwargs (Any): Forward everything to
                [`OpenAILike`][llama_index.llms.openai_like.OpenAILike].
        """
        self.model = OpenAILike(*args, **kwargs)

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        """Call an OpenAILike chat LLM with optional json schema for guided decoding.

        Args:
            messages: Message history to pass to the LLM query.
            json_schema: Schema the LLM output must comply with.
                None means free-form output. - must be passed by keyword

        Keyword Args:
            extra_body (dict): Optionally containing `structured_outputs`.

        Returns:
            [`ChatResponse`][llama_index.core.base.llms.types.ChatResponse] holding the model's
                reply message and raw API response.

        Raises:
            ValueError: Raised upon a BadRequestError. Converted to match in-process backends.
                Auth, rate-limit, and connection errors pass through unchanged.

        Warns:
            UserWarning: If the `request_kwargs` contain `structured_outputs` in the `extra_body`,
                and a `json_schema` is supplied, warn that `json_schema` overwrites `structured_outputs`.
        """
        if json_schema is not None:
            # vllm hosted models require json schema guided decoding via extra_body
            if "extra_body" not in request_kwargs:
                request_kwargs["extra_body"] = {}
            if "structured_outputs" in request_kwargs["extra_body"]:
                warn_once(
                    f'Overwriting existing "structured_outputs": '
                    f'{request_kwargs["extra_body"]["structured_outputs"]} '
                    'in request_parameters["extra_body"] with provided json schema for '
                    'guided decoding ("structured_outputs": {"json": schema}).'
                )
            request_kwargs["extra_body"]["structured_outputs"] = {"json": json_schema}

        llama_index_messages = [
            LlamaIndexChatMessage(role=msg.role, content=msg.content) for msg in messages
        ]
        try:
            return self.model.chat(llama_index_messages, **request_kwargs)
        except BadRequestError as e:
            # align error type with in_process LLMs
            raise ValueError(e.message) from e

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str:
        """Extract reasoning from a chat response.

        Args:
            response: [`ChatResponse`][llama_index.core.base.llms.types.ChatResponse] to
                extract the reasoning from.

        Returns:
            Reasoning output from the given
                [`ChatResponse`][llama_index.core.base.llms.types.ChatResponse].

        Raises:
            ReasoningExtractionError: If the reasoning cannot be extracted.
            EmptyReasoningError: If the extracted reasoning is empty.
        """

        raw_msg = self.get_raw_message_from_chat_response(response)

        # vLLM: prefer `reasoning`, fallback to legacy `reasoning_content`
        result = getattr(raw_msg, "reasoning", None) or getattr(raw_msg, "reasoning_content", None)
        if not isinstance(result, str):
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        if not result.strip():
            raise EmptyReasoningError("Extracted reasoning is empty.")

        return result
