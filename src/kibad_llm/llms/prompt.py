"""Render extraction prompts and prepare the messages sent to an LLM."""

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
    """A message role and its text content."""

    role: MessageRole
    content: str


@dataclass(frozen=True)
class ExtractionPrompt:
    """Templates and inputs available when preparing an extraction request.

    The schema is the one selected for the prompt. The extractor passes the
    decoding schema separately when it executes the request.
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
        current_messages: The rendered current turn, used for extraction result recording.
        messages: The complete chat input, including any history.
        input_artifacts: Optional named text inputs for the backend to consume.
    """

    current_messages: list[SimpleChatMessage]
    messages: list[SimpleChatMessage]
    input_artifacts: dict[str, str] = field(default_factory=dict)


def build_chat_messages(
    templates: Sequence[SimpleChatMessage],
    bindings: Mapping[str, str],
) -> list[SimpleChatMessage]:
    """Render message templates with the supplied placeholder values."""
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
    """Render an extraction request that provides the document inline."""
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
