"""Base interface for preparing and executing LLM chat requests."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
import json
from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from pydantic import BaseModel

from kibad_llm.llms.request import (
    ExtractionPrompt,
    PreparedRequest,
    SimpleChatMessage,
    get_template_placeholders,
    prepare_template_request,
)
from kibad_llm.schema.description import build_schema_description


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


def build_inline_schema_bindings(
    prompt: ExtractionPrompt, placeholders: set[str]
) -> dict[str, str]:
    """Build the requested text representations of the selected prompt schema.

    Args:
        prompt: The selected schema, inline field names, and description options.
        placeholders: Names of the representations the backend needs.

    Returns:
        Bindings for the requested JSON and readable description fields. If the
        prompt has no schema, neither binding is supplied.

    Raises:
        TypeError: The schema cannot be serialized or the description options are invalid.
        ValueError: The schema cannot be expanded into a requested description.
    """
    bindings: dict[str, str] = {}
    if prompt.schema is None:
        return bindings
    if prompt.schema_placeholder in placeholders:
        bindings[prompt.schema_placeholder] = json.dumps(prompt.schema, ensure_ascii=False)
    if prompt.schema_description_placeholder in placeholders:
        bindings[prompt.schema_description_placeholder] = build_schema_description(
            schema=prompt.schema, **(prompt.schema_description_kwargs or {})
        )
    return bindings


def prepare_inline_request(prompt: ExtractionPrompt) -> PreparedRequest:
    """Deliver the document and any requested schema representations as message text.

    Args:
        prompt: Templates, inputs, history, and the document requirement for this turn.

    Returns:
        The rendered current turn and full conversation.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        ValueError: A required document is unused, or the templates cannot be rendered.
    """
    templates = prompt.message_templates()
    placeholders = get_template_placeholders(templates)
    bindings = build_inline_schema_bindings(prompt, placeholders)
    bindings[prompt.document_placeholder] = prompt.document
    request = prepare_template_request(templates, bindings=bindings, history=prompt.history)
    if prompt.require_document and prompt.document_placeholder not in placeholders:
        raise ValueError(
            "The message templates must contain the document placeholder "
            f"'{{{prompt.document_placeholder}}}' for this extraction turn."
        )
    return request


class LLM(ABC):
    """Prepare and execute chat requests with a model backend."""

    def prepare_request(self, prompt: ExtractionPrompt) -> PreparedRequest:
        """Prepare the current turn and its inputs for this backend.

        The caller selects the document and prompt schema and declares whether this
        turn requires the document. The backend must satisfy that requirement, supply
        values for the fields used in its templates, and include any required files
        in the request. Use distinct names for the fields a backend supplies.

        The default embeds the document and requested schema representations in the
        messages. Overrides can reuse [`build_inline_schema_bindings`][kibad_llm.llms.base.build_inline_schema_bindings]
        and [`prepare_template_request`][kibad_llm.llms.request.prepare_template_request]
        with their own bindings. History is already rendered and can be prepended as supplied.

        Args:
            prompt: Inputs, templates, history, and context requirements for this turn.

        Returns:
            The current turn, full conversation including history, and any auxiliary
            backend inputs. The default implementation creates no auxiliary inputs.

        Raises:
            MissingBindingError: A template references an unavailable binding.
            ValueError: A required document is unused, or the templates cannot be rendered.
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
