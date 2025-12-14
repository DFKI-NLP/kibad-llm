from abc import ABC, abstractmethod
import dataclasses
from typing import Any

from llama_index.core.base.llms.types import ChatResponse, MessageRole


class MissingRawChatResponseError(Exception):
    """Raised when a ChatResponse is missing the raw attribute."""

    pass


class RawMessageExtractionError(Exception):
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

    def get_raw_message_from_chat_response(self, response: ChatResponse) -> Any:
        """Extract raw message from a chat response."""

        raw = response.raw
        if raw is None:
            raise MissingRawChatResponseError("ChatResponse is missing raw attribute.")

        try:
            msg = raw.choices[0].message
            return msg
        except (AttributeError, IndexError, TypeError):
            raise RawMessageExtractionError(
                "Could not extract message from chat response raw attribute."
            )

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str:
        """Extract reasoning from a chat response.

        Reasoning may be normalized into `additional_kwargs` by backend wrappers.
        For OpenAI-like backends, we fall back to provider-specific fields on `response.raw`.
        """

        # 1) Preferred: normalized location (works for in-process vLLM).
        reasoning = response.additional_kwargs.get(
            "reasoning"
        ) or response.message.additional_kwargs.get("reasoning")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning

        # 2) Fallback: OpenAI-like raw response shape (choices[0].message.reasoning[_content]).
        msg = self.get_raw_message_from_chat_response(response)

        # vLLM: prefer `reasoning`, fallback to legacy `reasoning_content`
        result = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
        if isinstance(result, str) and result.strip():
            return result

        raise ReasoningExtractionError("Could not extract reasoning from chat response.")

    def get_response_content_from_chat_response(self, response: ChatResponse) -> str:
        """Extract content from chat response."""

        response_content = response.message.content
        if response_content is None:
            raise MissingResponseContentError("LLM response is missing content.")
        if not response_content.strip():
            raise EmptyResponseMessageError("LLM returned an empty message.")
        return response_content
