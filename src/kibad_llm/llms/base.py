"""Base interface for preparing and executing LLM chat requests."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from pydantic import BaseModel

from kibad_llm.llms.request import (
    ExtractionPrompt,
    PreparedRequest,
    SimpleChatMessage,
    prepare_inline_request,
)


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


class EmptyReasoningError(Exception):
    """Raised when the extracted reasoning is empty."""

    ...


class LLM(ABC):
    """Prepare and execute chat requests with a model backend."""

    def prepare_request(self, prompt: ExtractionPrompt) -> PreparedRequest:
        """Build the current turn and full request, using inline document text by default.

        Backends can override this method to change how they build messages or
        supply auxiliary inputs for their chat call. The default implementation delegates
        to [`prepare_inline_request`][kibad_llm.llms.request.prepare_inline_request].

        Args:
            prompt: Templates and inputs available for preparing the extraction request.

        Returns:
            The current turn, full conversation including history, and any auxiliary
            backend inputs. The default implementation creates no auxiliary inputs.

        Raises:
            ValueError: Default inline preparation rejects missing templates, a missing
                required schema, a missing first-turn document placeholder, invalid
                formatting, or an unsupported schema description.
            TypeError: A referenced schema cannot be serialized as JSON, or schema
                description options contain unsupported arguments.

        Warns:
            UserWarning: Default inline preparation logs a warning once if a supplied
                schema is unused by the templates.
        """
        return prepare_inline_request(prompt)

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

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str | None:
        """Extract reasoning from a chat response."""
        raise NotImplementedError(
            f"get_reasoning_from_chat_response() is not implemented for {type(self)}"
        )

    def get_backend_metadata_from_chat_response(
        self, response: ChatResponse
    ) -> dict[str, Any] | None:
        """Return token usage without changing the backend's field names or details.

        The default supports the raw API responses used by OpenAI and API-hosted
        vLLM. Other backends can override this method for their response format.

        Args:
            response: The response from one chat call.

        Returns:
            JSON-serializable metadata containing a copy of the backend's `usage`,
            or None if the response does not report usage. Missing counts are not
            estimated or replaced with zero.

        Raises:
            TypeError: Reported usage is neither a Pydantic model nor a mapping.
        """
        raw = response.raw
        usage = raw.get("usage") if isinstance(raw, Mapping) else getattr(raw, "usage", None)
        if usage is None:
            return None
        if isinstance(usage, BaseModel):
            usage = usage.model_dump(mode="json")
        elif isinstance(usage, Mapping):
            usage = deepcopy(dict(usage))
        else:
            raise TypeError(f"Unsupported token usage type: {type(usage).__name__}")
        return {"usage": usage}

    def get_response_content_from_chat_response(self, response: ChatResponse) -> str:
        """Extract content from chat response."""

        response_content = response.message.content
        if response_content is None:
            raise MissingResponseContentError("LLM response is missing content.")
        if not response_content.strip():
            raise EmptyResponseMessageError("LLM returned an empty message.")
        return response_content
