"""Define the LLM backend interface and its default inline request preparation.

Each backend supplies values and input artifacts for the fields in the current template.
The default inline preparation requires a document field on the first turn and supplies
schema JSON or a readable description when the template references the corresponding fields.
`LLM` also defines the chat call and access to response content, reasoning, and metadata.

Classes:
    MissingRawChatResponseError: Raised when a ChatResponse is missing the raw attribute.
    RawMessageExtractionError: Raised when a message cannot be extracted from a ChatResponse raw attribute.
    MissingResponseContentError: Raised when the LLM response message has no content.
    EmptyResponseMessageError: Raised when the LLM response message is empty.
    ReasoningExtractionError: Raised when reasoning cannot be extracted from the LLM response message.
    EmptyReasoningError: Raised when the extracted reasoning is empty.
    SimpleChatMessage: Simplified representation of a chat message.
    LLM: Base class for LLM interaction. This class defines the project internal LLM API.

"""

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from copy import deepcopy
import json
from typing import Any

from llama_index.core.base.llms.types import ChatResponse
from pydantic import BaseModel

from kibad_llm.llms.request import (
    PreparedRequest,
    SimpleChatMessage,
    get_message_templates,
    get_template_placeholders,
    prepare_template_request,
)
from kibad_llm.schema.description import build_schema_description

DOCUMENT_PLACEHOLDER = "document"
SCHEMA_PLACEHOLDER = "schema"
SCHEMA_DESCRIPTION_PLACEHOLDER = "schema_description"
SCHEMA_DESCRIPTION_KWARGS_KEY = "schema_description_kwargs"


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


def prepare_request(
    prompt_template: Mapping[str, Any],
    *,
    document: str,
    schema: dict[str, Any] | None,
    history: Sequence[SimpleChatMessage] = (),
) -> PreparedRequest:
    """Render the requested document and schema fields as message text.

    The first turn must reference `{document}` in its system or user message.
    A turn with history may omit it.

    Args:
        prompt_template: Current messages. They can use `{schema}` for JSON Schema and
            `{schema_description}` for a readable description. `schema_description_kwargs`
            configures the description.
        document: Source text to insert at `{document}`.
        schema: Schema selected for the prompt, or None.
        history: Previously rendered messages to prepend.

    Returns:
        The rendered current turn and full conversation.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        TypeError: The template contains unrecognized inline prompt settings.
        ValueError: A referenced schema field has no schema, the first turn omits
            the document field, or the templates cannot be rendered.
    """
    templates, remaining_settings = get_message_templates(prompt_template)
    schema_description_kwargs = remaining_settings.pop(SCHEMA_DESCRIPTION_KWARGS_KEY, None)
    if remaining_settings:
        unknown_settings = ", ".join(sorted(repr(key) for key in remaining_settings))
        raise TypeError(
            f"Inline prompt_template contains unrecognized settings {unknown_settings}."
        )

    placeholders = get_template_placeholders(templates)
    bindings: dict[str, str] = {}
    if SCHEMA_PLACEHOLDER in placeholders:
        if schema is None:
            raise ValueError(f"Placeholder '{{{SCHEMA_PLACEHOLDER}}}' requires a schema.")
        bindings[SCHEMA_PLACEHOLDER] = json.dumps(schema, ensure_ascii=False)
    if SCHEMA_DESCRIPTION_PLACEHOLDER in placeholders:
        if schema is None:
            raise ValueError(
                f"Placeholder '{{{SCHEMA_DESCRIPTION_PLACEHOLDER}}}' requires a schema."
            )
        bindings[SCHEMA_DESCRIPTION_PLACEHOLDER] = build_schema_description(
            schema=schema, **(schema_description_kwargs or {})
        )
    if DOCUMENT_PLACEHOLDER in placeholders:
        bindings[DOCUMENT_PLACEHOLDER] = document
    request = prepare_template_request(templates, bindings=bindings, history=history)
    if not history and DOCUMENT_PLACEHOLDER not in placeholders:
        raise ValueError(
            f"The first inline turn must reference '{{{DOCUMENT_PLACEHOLDER}}}' "
            "in the system or user message."
        )
    return request


class LLM(ABC):
    """Prepare and execute chat requests with a model backend."""

    def prepare_request(
        self,
        prompt_template: Mapping[str, Any],
        *,
        document: str,
        schema: dict[str, Any] | None,
        history: Sequence[SimpleChatMessage] = (),
    ) -> PreparedRequest:
        """Prepare the current turn and its inputs for this backend.

        The backend supplies the fields referenced by the message templates. Include any
        files the referenced fields require in the returned request.

        The default calls the module-level [`prepare_request`][kibad_llm.llms.base.prepare_request],
        which requires the document field on the first turn. Overrides can pass
        their bindings and rendered history to
        [`prepare_template_request`][kibad_llm.llms.request.prepare_template_request].

        Args:
            prompt_template: Current system/user templates and their backend-specific settings.
            document: Source text selected by the extractor for this turn.
            schema: Schema selected for use in the prompt. The extractor supplies the
                decoding schema separately when it calls the model.
            history: Previously rendered messages to prepend.

        Returns:
            The current turn, full conversation including history, and any auxiliary
            backend inputs. The default implementation creates no auxiliary inputs.

        Raises:
            MissingBindingError: A template references an unavailable binding.
            TypeError: The inline template contains unrecognized prompt settings.
            ValueError: A template is invalid for the backend.
        """
        return prepare_request(prompt_template, document=document, schema=schema, history=history)

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
            response: A ChatResponse to extract the raw message from.

        Returns:
            The raw message embedded in the provided ChatResponse.


        Raises:
            MissingRawChatResponseError: Raised if the ChatResponse is missing the raw attribute.
            RawMessageExtractionError: Raised if the raw message cannot be extracted.
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
            response: A ChatResponse to extract the reasoning from.

        Returns:
            The reasoning embedded in the provided ChatResponse.


        Raises:
            NotImplementedError: This is a stub that needs to be implemented per backend, if the backend supports it.
        """
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
        """Extract content from chat response.

        Args:
            response: A ChatResponse to extract the content from.

        Returns:
            The response embedded in the provided ChatResponse.


        Raises:
            MissingResponseContentError: Raised if the ChatResponse carries no content.
            EmptyResponseMessageError: Raised if the ChatResponse carries an empty message as content.
        """
        response_content = response.message.content
        if response_content is None:
            raise MissingResponseContentError("LLM response is missing content.")
        if not response_content.strip():
            raise EmptyResponseMessageError("LLM returned an empty message.")
        return response_content
