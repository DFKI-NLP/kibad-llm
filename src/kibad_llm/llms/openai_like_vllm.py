from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from llama_index.llms.openai_like import OpenAILike

from kibad_llm.llms.base import (
    LLM,
    EmptyReasoningError,
    ReasoningExtractionError,
    SimpleChatMessage,
)
from kibad_llm.utils.log import warn_once


class OpenAILikeVllm(LLM):
    """Simple wrapper around OpenAI-like LLMs to indicate vLLM usage in extractors.extract_from_text"""

    def __init__(self, *args, **kwargs) -> None:
        self.model = OpenAILike(*args, **kwargs)

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
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
        return self.model.chat(llama_index_messages, **request_kwargs)

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str:
        """Extract reasoning from a chat response."""

        raw_msg = self.get_raw_message_from_chat_response(response)

        # vLLM: prefer `reasoning`, fallback to legacy `reasoning_content`
        result = getattr(raw_msg, "reasoning", None) or getattr(raw_msg, "reasoning_content", None)
        if not isinstance(result, str):
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        if not result.strip():
            raise EmptyReasoningError("Extracted reasoning is empty.")

        return result
