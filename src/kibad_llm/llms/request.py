"""Prepare extraction requests for LLM backends.

Classes:
    MissingBindingError: A template references a field without a supplied value.
    SimpleChatMessage: A role and template or rendered message text.
    ExtractionPrompt: Templates and inputs for preparing an extraction request.
    PreparedRequest: Rendered messages and optional backend inputs.

Functions:
    build_chat_messages: Render role-tagged templates with explicit bindings.
    prepare_template_request: Render templates and schema bindings and prepend history.
    prepare_inline_request: Prepare messages with the document embedded in the text.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import json
from string import Formatter
from typing import Any

from llama_index.core.base.llms.types import MessageRole

from kibad_llm.schema.description import build_schema_description
from kibad_llm.utils.log import warn_once


class MissingBindingError(ValueError):
    """A template references a field without a supplied value.

    Attributes:
        placeholder: Name of the missing binding, without braces.
        role: Role of the message whose template requires the binding.
    """

    def __init__(self, placeholder: str, role: MessageRole):
        """Identify the missing binding and the message that requires it."""
        super().__init__(f"No value for placeholder {placeholder!r} in {role.name} message.")
        self.placeholder = placeholder
        self.role = role


@dataclass
class SimpleChatMessage:
    """Simplified representation of a chat message.

    Attributes:
        role: Role of the actor who wrote the content, such as user, system, or assistant.
            Any `MessageRole` value is accepted.
        content: Message text, which may be a template before request preparation or
            rendered content ready to send to the backend.
    """

    role: MessageRole
    content: str


@dataclass(frozen=True)
class ExtractionPrompt:
    """Templates and inputs available when preparing an extraction request.

    The schema is the one selected for the prompt. The extractor passes the
    decoding schema separately when it executes the request.

    Attributes:
        document: Source document text to extract from, typically Markdown.
        schema: JSON Schema available to the templates, or None when no schema is supplied.
        system_message: System message template, or None to omit the system message.
        user_message: User message template, or None to omit the user message.
        history: Previously rendered messages to prepend to the current turn, in order.
            Defaults to an empty sequence. Inline preparation leaves these messages unchanged.
        document_placeholder: Template field name for the document, without braces.
            Defaults to `document`.
        schema_placeholder: Template field name for the schema serialized as JSON, without
            braces. Defaults to `schema`.
        schema_description_placeholder: Template field name for the human-readable schema
            description, without braces. Defaults to `schema_description`.
        schema_description_kwargs: Optional keyword arguments forwarded to
            [`build_schema_description`][kibad_llm.schema.description.build_schema_description]
            when a template uses the schema description placeholder.
    """

    document: str
    schema: dict[str, Any] | None
    system_message: str | None = None
    user_message: str | None = None
    history: Sequence[SimpleChatMessage] = ()
    document_placeholder: str = "document"
    schema_placeholder: str = "schema"
    schema_description_placeholder: str = "schema_description"
    schema_description_kwargs: dict[str, Any] | None = None


@dataclass
class PreparedRequest:
    """Prepared input to a backend's chat call.

    Attributes:
        current_messages: The rendered current turn without history, used for extraction
            result recording. These messages retain the full text before snapshot truncation.
        messages: The complete chat input, with history followed by the current turn.
        input_artifacts: Named text inputs for backends that support auxiliary inputs.
            Defaults to an empty dictionary. When nonempty, the extractor passes this dictionary
            to the backend's chat call as the `input_artifacts` keyword argument.
    """

    current_messages: list[SimpleChatMessage]
    messages: list[SimpleChatMessage]
    input_artifacts: dict[str, str] = field(default_factory=dict)


def build_chat_messages(
    templates: Sequence[SimpleChatMessage],
    bindings: Mapping[str, str],
) -> list[SimpleChatMessage]:
    """Render message templates with the supplied placeholder values.

    Uses Python's `str.format_map` syntax. Double braces escape literal braces;
    braces inside binding values are not interpreted again.

    Args:
        templates: Messages whose content contains named replacement fields.
        bindings: Replacement values keyed by field name, without braces.

    Returns:
        New messages in template order, preserving each role and replacing its content.
        The input templates are not modified.

    Raises:
        MissingBindingError: A replacement field has no binding, with the field name
            and message role included in the error.
        ValueError: A template contains invalid formatting syntax.
    """
    messages = []
    for template in templates:
        try:
            content = template.content.format_map(bindings)
        except KeyError as error:
            raise MissingBindingError(error.args[0], template.role) from error
        messages.append(SimpleChatMessage(role=template.role, content=content))
    return messages


def _get_placeholder_roles(prompt: ExtractionPrompt) -> dict[str, MessageRole]:
    """Find unescaped template fields and the first message role that references each."""
    formatter = Formatter()
    roles_by_placeholder: dict[str, MessageRole] = {}
    for role, content in (
        (MessageRole.SYSTEM, prompt.system_message),
        (MessageRole.USER, prompt.user_message),
    ):
        if content is not None:
            for _, name, _, _ in formatter.parse(content):
                if name is not None:
                    roles_by_placeholder.setdefault(name, role)
    return roles_by_placeholder


def prepare_template_request(
    prompt: ExtractionPrompt, *, bindings: Mapping[str, str]
) -> PreparedRequest:
    """Render extraction templates with schema bindings and caller-supplied values.

    Render the configured system and user templates in that order, omitting templates
    set to None. Resolve the JSON Schema and its human-readable description only when
    referenced. Caller bindings supply any other values; document delivery and its
    validation belong to the caller. Escaped placeholders remain literal text.

    Args:
        prompt: Templates, optional schema, history, and placeholder settings for this turn.
        bindings: Explicit replacement values, excluding the configured schema placeholders.
            The mapping is not modified. Pass an empty mapping for file-backed prompts
            that need only schema bindings.

    Returns:
        A request with the rendered current turn and the full conversation formed by
        prepending unchanged history. No auxiliary input artifacts are created.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        ValueError: Both templates are None, caller bindings override schema placeholders,
            a schema placeholder is used without a schema, a template cannot be rendered,
            or the schema cannot be expanded into a description.
        TypeError: A referenced schema cannot be serialized as JSON, or
            `schema_description_kwargs` contains unsupported arguments.

    Warns:
        UserWarning: Logs a warning once when a schema is supplied but neither schema
            placeholder is used by the templates.
    """
    templates = [
        SimpleChatMessage(role=role, content=content)
        for role, content in (
            (MessageRole.SYSTEM, prompt.system_message),
            (MessageRole.USER, prompt.user_message),
        )
        if content is not None
    ]
    if not templates:
        raise ValueError("At least one of system_message or user_message must be provided.")

    schema_placeholders = {prompt.schema_placeholder, prompt.schema_description_placeholder}
    conflicting_bindings = schema_placeholders.intersection(bindings)
    if conflicting_bindings:
        raise ValueError(
            f"Caller bindings must not override schema placeholders: {sorted(conflicting_bindings)}."
        )

    roles_by_placeholder = _get_placeholder_roles(prompt)
    schema_description_role = roles_by_placeholder.get(prompt.schema_description_placeholder)
    schema_role = roles_by_placeholder.get(prompt.schema_placeholder)
    resolved_bindings = dict(bindings)
    if prompt.schema is None:
        for role, description, placeholder in (
            (schema_description_role, "schema description", prompt.schema_description_placeholder),
            (schema_role, "JSON Schema", prompt.schema_placeholder),
        ):
            if role is not None:
                raise ValueError(
                    f"Schema must be provided if {role.name} message template requires "
                    f"{description} (it contains '{{{placeholder}}}')."
                )
    else:
        if schema_description_role is not None:
            resolved_bindings[prompt.schema_description_placeholder] = build_schema_description(
                schema=prompt.schema, **(prompt.schema_description_kwargs or {})
            )
        if schema_role is not None:
            resolved_bindings[prompt.schema_placeholder] = json.dumps(
                prompt.schema, ensure_ascii=False
            )
        if schema_description_role is None and schema_role is None:
            warn_once(
                "Schema provided but message templates use neither schema placeholder "
                f"('{{{prompt.schema_description_placeholder}}}' or '{{{prompt.schema_placeholder}}}')."
            )

    current_messages = build_chat_messages(templates, resolved_bindings)
    return PreparedRequest(
        current_messages=current_messages,
        messages=[*prompt.history, *current_messages],
    )


def prepare_inline_request(prompt: ExtractionPrompt) -> PreparedRequest:
    """Prepare an extraction request with the document embedded in its templates.

    Supply the document binding to
    [`prepare_template_request`][kibad_llm.llms.request.prepare_template_request]
    and require its placeholder when history is empty. Escaped placeholders such as
    `{{document}}` remain literal text and do not satisfy that requirement.

    Args:
        prompt: Templates, document, optional schema, history, and placeholder settings
            to use for this turn.

    Returns:
        A request with the rendered current turn and unchanged history prepended to it.
        No auxiliary input artifacts are created.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        ValueError: No document placeholder is used when history is empty, or shared
            template preparation rejects the templates, bindings, or schema.
        TypeError: A referenced schema cannot be serialized as JSON, or
            `schema_description_kwargs` contains unsupported arguments.

    Warns:
        UserWarning: Logs a warning once when a schema is supplied but neither schema
            placeholder is used by the templates.
    """
    request = prepare_template_request(
        prompt, bindings={prompt.document_placeholder: prompt.document}
    )
    if not prompt.history and prompt.document_placeholder not in _get_placeholder_roles(prompt):
        raise ValueError(
            "At least one of the message templates must require the input text "
            f"(they must contain '{{{prompt.document_placeholder}}}')."
        )

    return request
