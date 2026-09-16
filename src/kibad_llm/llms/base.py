"""TODO

Classes:
    MissingRawChatResponseError:
    RawMessageExtractionError:
    MissingResponseContentError:
    EmptyResponseMessageError:
    ReasoningExtractionError:
    EmptyReasoningError:
    SimpleChatMessage:
    LLM:
"""

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

    pass


class EmptyResponseMessageError(Exception):
    """Raised when the LLM response message is empty."""

    pass


class ReasoningExtractionError(Exception):
    """Raised when reasoning cannot be extracted from the LLM response message."""

    pass


class EmptyReasoningError(Exception):
    """Raised when the extracted reasoning is empty."""

    pass


@dataclasses.dataclass
class SimpleChatMessage:
    """Simplified representation of a chat message.

    Attributes:
        role: Role of the actor who wrote the content. user, system, or assistant.
        content: Written content, meaning chat output, of the SimpleChatMessage.
    """

    role: MessageRole
    content: str


class LLM(ABC):
    """Base class for LLM interaction.

    Methods:
        call_llm_chat_with_guided_decoding: TODO
        get_raw_message_from_chat_response: TODO
        get_reasoning_from_chat_response: TODO
        get_response_content_from_chat_response: TODO
    """

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
        """Extract raw message from a chat response.

        Args:
            response:

        Returns:


        Raises:
            MissingRawChatResponseError:
            RawMessageExtractionError:
        """

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

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str | None:
        """Extract reasoning from a chat response.

        Args:
            response:

        Returns:


        Raises:
            NotImplementedError:
        """
        raise NotImplementedError(
            f"get_reasoning_from_chat_response() is not implemented for {type(self)}"
        )

    def get_response_content_from_chat_response(self, response: ChatResponse) -> str:
        """Extract content from chat response.

        Args:
            response:

        Returns:


        Raises:
            MissingResponseContentError:
            EmptyResponseMessageError:
        """
        response_content = response.message.content
        if response_content is None:
            raise MissingResponseContentError("LLM response is missing content.")
        if not response_content.strip():
            raise EmptyResponseMessageError("LLM returned an empty message.")
        return response_content
