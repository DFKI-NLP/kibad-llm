"""Share request types and message rendering between LLM backends.

Classes:
    MissingBindingError: A template references a field without a supplied value.
    SimpleChatMessage: A role and template or rendered message text.
    ExtractionPrompt: Templates and inputs for preparing an extraction request.
    PreparedRequest: Rendered messages and optional backend inputs.

Functions:
    build_chat_messages: Render role-tagged templates with explicit bindings.
    get_template_placeholders: Find the binding names referenced by message templates.
    prepare_template_request: Render with supplied bindings and prepend history.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from string import Formatter
from typing import Any

from llama_index.core.base.llms.types import MessageRole


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
    """Inputs, templates, and context requirements for preparing an extraction turn.

    The extractor selects the prompt schema and passes the decoding schema separately
    when executing the request. The backend chooses what bindings and files to supply.

    Attributes:
        document: Source document text to extract from, typically Markdown.
        schema: JSON Schema available to the templates, or None when no schema is supplied.
        system_message: System message template, or None to omit the system message.
        user_message: User message template, or None to omit the user message.
        history: Previously rendered messages to prepend to the current turn, in order.
            History contains message text. Files are supplied separately for each call.
        require_document: Whether the current turn must deliver the source document.
            Defaults to True. The extractor can set this to False for follow-up turns
            whose previous messages supply the context they need.
        document_placeholder: Name of the inline document field, without braces.
            Defaults to `document`. Applies to backends that supply the document inline.
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
    require_document: bool = True

    def message_templates(self) -> list[SimpleChatMessage]:
        """Return the configured system and user templates in that order.

        Returns:
            The role-tagged templates, omitting messages configured as None.

        Raises:
            ValueError: Neither message template is configured.
        """
        templates = [
            SimpleChatMessage(role=role, content=content)
            for role, content in (
                (MessageRole.SYSTEM, self.system_message),
                (MessageRole.USER, self.user_message),
            )
            if content is not None
        ]
        if not templates:
            raise ValueError("At least one of system_message or user_message must be provided.")
        return templates


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


def get_template_placeholders(templates: Sequence[SimpleChatMessage]) -> set[str]:
    """Find the bindings needed to render the supplied message templates.

    Use Python format fields. Escaped braces remain literal. Attribute access, indexing,
    conversions, and nested format specifications refer to their root binding names.

    Args:
        templates: The message templates for the current turn.

    Returns:
        The set of referenced binding names.

    Raises:
        ValueError: A template contains invalid formatting syntax.
    """
    formatter = Formatter()
    placeholders: set[str] = set()
    pending = [template.content for template in templates]
    while pending:
        for _, name, format_spec, _ in formatter.parse(pending.pop()):
            if name is not None:
                placeholders.add(name.partition(".")[0].partition("[")[0])
                if format_spec:
                    pending.append(format_spec)
    return placeholders


def prepare_template_request(
    templates: Sequence[SimpleChatMessage],
    *,
    bindings: Mapping[str, str],
    history: Sequence[SimpleChatMessage] = (),
) -> PreparedRequest:
    """Build a request by rendering the current turn and prepending rendered history.

    Args:
        templates: Current message templates in their desired order.
        bindings: All replacement values, keyed by field name without braces.
        history: Previously rendered messages in order, copied into the request as supplied.

    Returns:
        The rendered current turn and full conversation. Backends can add input artifacts.

    Raises:
        MissingBindingError: A template references an unavailable binding.
        ValueError: A template cannot be rendered with Python's formatting syntax.
    """
    current_messages = build_chat_messages(templates, bindings)
    return PreparedRequest(
        current_messages=current_messages,
        messages=[*history, *current_messages],
    )
