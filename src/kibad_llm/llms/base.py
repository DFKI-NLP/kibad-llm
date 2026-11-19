"""Define the LLM backend interface and its default inline request preparation.

Each backend supplies values and input artifacts for the fields in the current template.
The default inline preparation requires a document field on the first turn. Its schema
bindings supply JSON or a readable description and can be reused by other backends.
`LLM` also defines the chat call and access to response content, reasoning, and metadata.
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
    prompt_template: Mapping[str, Any], placeholders: set[str], *, schema: dict[str, Any] | None
) -> dict[str, str]:
    """Build the requested text representations of the selected prompt schema.

    Args:
        prompt_template: Per-template settings for the JSON field (`schema_placeholder`),
            the description field (`schema_description_placeholder`), and options for
            [`build_schema_description`][kibad_llm.schema.description.build_schema_description]
            (`schema_description_kwargs`).
        placeholders: Names of the representations the backend needs.
        schema: Schema selected for this prompt, or None to omit schema bindings.

    Returns:
        Bindings for the requested JSON and readable description fields. If the
        prompt has no schema, neither binding is supplied.

    Raises:
        TypeError: The schema cannot be serialized or the description options are invalid.
        ValueError: The schema cannot be expanded into a requested description.
    """
    bindings: dict[str, str] = {}
    if schema is None:
        return bindings
    schema_field = prompt_template.get("schema_placeholder", "schema")
    description_field = prompt_template.get("schema_description_placeholder", "schema_description")
    if schema_field in placeholders:
        bindings[schema_field] = json.dumps(schema, ensure_ascii=False)
    if description_field in placeholders:
        bindings[description_field] = build_schema_description(
            schema=schema, **(prompt_template.get("schema_description_kwargs") or {})
        )
    return bindings


def prepare_inline_request(
    prompt_template: Mapping[str, Any],
    *,
    document: str,
    schema: dict[str, Any] | None,
    history: Sequence[SimpleChatMessage] = (),
) -> PreparedRequest:
    """Render the requested document and schema fields as message text.

    With empty history, at least one template must reference the configured document
    field. A follow-up can use the document already present in the conversation.

    Args:
        prompt_template: Current message templates and their inline field settings.
        document: Source text bound to the configured `document_placeholder` (default `document`).
        schema: Schema selected for the prompt, or None.
        history: Previously rendered messages to prepend.

    Returns:
        The rendered current turn and full conversation.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        ValueError: The first turn omits the document field, or the templates cannot be rendered.
    """
    templates = get_message_templates(prompt_template)
    placeholders = get_template_placeholders(templates)
    bindings = build_inline_schema_bindings(prompt_template, placeholders, schema=schema)
    document_field = prompt_template.get("document_placeholder", "document")
    bindings[document_field] = document
    request = prepare_template_request(templates, bindings=bindings, history=history)
    if not history and document_field not in placeholders:
        raise ValueError(
            "The message templates must contain the document placeholder "
            f"'{{{document_field}}}' on the first turn."
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

        The caller selects the document and prompt schema. Read the template settings
        for this call, supply values for referenced fields, and include any files those
        fields refer to in the returned request.

        The default uses [`prepare_inline_request`][kibad_llm.llms.base.prepare_inline_request],
        which requires the inline document field on the first turn. Overrides can reuse
        [`build_inline_schema_bindings`][kibad_llm.llms.base.build_inline_schema_bindings]
        and [`prepare_template_request`][kibad_llm.llms.request.prepare_template_request]
        with their own bindings. History is already rendered and can be prepended as supplied.

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
            ValueError: A template is invalid for the backend.
        """
        return prepare_inline_request(
            prompt_template, document=document, schema=schema, history=history
        )

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
