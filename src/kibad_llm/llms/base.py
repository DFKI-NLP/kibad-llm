from abc import ABC, abstractmethod
import dataclasses
from typing import Any

from llama_index.core.base.llms.types import ChatResponse, MessageRole


class MissingRawChatResponseError(Exception):
    """Raised when a ChatResponse is missing the raw attribute."""

    pass


class ChatMessageExtractionError(Exception):
    """Raised when a message cannot be extracted from a ChatResponse raw attribute."""

    pass


class MissingResponseContentError(Exception):
    """Raised when the LLM response message has no content."""

    ...


class EmptyResponseMessageError(Exception):
    """Raised when the LLM response message is empty."""

    ...


class ReasoningExtractionError(Exception):
    """Raised when reasoning cannot be extracted from the LLM response message."""

    ...


@dataclasses.dataclass
class SimpleChatMessage:
    role: MessageRole
    content: str


class LLM(ABC):

    @abstractmethod
    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        """Call a chat LLM with optional json schema for guided decoding."""
        ...

    @staticmethod
    def get_reasoning_from_chat_response(response: ChatResponse) -> str:
        """Extract reasoning from chat response."""

        raw = response.raw
        if raw is None:
            raise MissingRawChatResponseError("ChatResponse is missing raw attribute.")

        try:
            msg = raw.choices[0].message
        except (AttributeError, IndexError, TypeError):
            raise ChatMessageExtractionError(
                "Could not extract message from chat response raw attribute."
            )

        # vLLM: prefer `reasoning`, fallback to legacy `reasoning_content`
        result = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
        if result is None:
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        return result

    @staticmethod
    def get_response_content_from_chat_response(response: ChatResponse) -> str:
        """Extract content from chat response."""

        response_content = response.message.content
        if response_content is None:
            raise MissingResponseContentError("LLM response is missing content.")
        if not response_content.strip():
            raise EmptyResponseMessageError("LLM returned an empty message.")
        return response_content
