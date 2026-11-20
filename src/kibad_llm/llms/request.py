"""Prepare extraction requests for LLM backends.

Classes:
    SimpleChatMessage: A role and template or rendered message text.
    ExtractionPrompt: Templates and inputs for preparing an extraction request.
    PreparedRequest: Rendered messages and optional backend inputs.

Functions:
    build_chat_messages: Render role-tagged templates with explicit bindings.
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
        ValueError: A replacement field has no binding, with the field name and message role
            included in the error, or a template contains invalid formatting syntax.
    """
    messages = []
    for template in templates:
        try:
            content = template.content.format_map(bindings)
        except KeyError as error:
            raise ValueError(
                f"No value for placeholder {error.args[0]!r} in {template.role.name} message."
            ) from error
        messages.append(SimpleChatMessage(role=template.role, content=content))
    return messages


def prepare_inline_request(prompt: ExtractionPrompt) -> PreparedRequest:
    """Render an extraction request that provides the document inline.

    Render the configured system and user templates in that order, omitting templates
    set to None. Bind the document text and, when referenced, the JSON Schema or its
    human-readable description. Without history, at least one template must use the
    document placeholder. Escaped placeholders such as `{{document}}` remain literal
    text and do not satisfy that requirement.

    Args:
        prompt: Templates, document, optional schema, history, and placeholder settings
            to use for this turn.

    Returns:
        A request with the rendered current turn and the full conversation formed by
        prepending unchanged history. No auxiliary input artifacts are created.

    Raises:
        ValueError: Both templates are None, a schema placeholder is used without a schema,
            no document placeholder is used when history is empty, a template cannot be
            rendered, or the schema cannot be expanded into a description.
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

    formatter = Formatter()
    roles_by_placeholder: dict[str, MessageRole] = {}
    for template in templates:
        for _, name, _, _ in formatter.parse(template.content):
            if name is not None:
                roles_by_placeholder.setdefault(name, template.role)

    schema_description_role = roles_by_placeholder.get(prompt.schema_description_placeholder)
    schema_role = roles_by_placeholder.get(prompt.schema_placeholder)
    bindings = {}
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
            bindings[prompt.schema_description_placeholder] = build_schema_description(
                schema=prompt.schema, **(prompt.schema_description_kwargs or {})
            )
        if schema_role is not None:
            bindings[prompt.schema_placeholder] = json.dumps(prompt.schema, ensure_ascii=False)
        if not bindings:
            warn_once(
                "Schema provided but message templates use neither schema placeholder "
                f"('{{{prompt.schema_description_placeholder}}}' or '{{{prompt.schema_placeholder}}}')."
            )

    bindings[prompt.document_placeholder] = prompt.document
    current_messages = build_chat_messages(templates, bindings)
    if not prompt.history and prompt.document_placeholder not in roles_by_placeholder:
        raise ValueError(
            "At least one of the message templates must require the input text "
            f"(they must contain '{{{prompt.document_placeholder}}}')."
        )

    return PreparedRequest(
        current_messages=current_messages,
        messages=[*prompt.history, *current_messages],
    )
