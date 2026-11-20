"""Tests for prompt rendering and default request preparation."""

import json

from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.llms.base import prepare_inline_request
from kibad_llm.llms.request import (
    MissingBindingError,
    SimpleChatMessage,
    build_chat_messages,
    get_message_templates,
    get_template_placeholders,
    prepare_template_request,
)


def test_get_message_templates_returns_remaining_settings() -> None:
    """Consume message keys on a copy of the backend's settings."""
    prompt_template = {
        "system_message": None,
        "user_message": "Read {filename}.",
        "filename_placeholder": "filename",
    }

    templates, remaining_settings = get_message_templates(prompt_template)

    assert templates == [SimpleChatMessage(role=MessageRole.USER, content="Read {filename}.")]
    assert remaining_settings == {"filename_placeholder": "filename"}
    assert prompt_template == {
        "system_message": None,
        "user_message": "Read {filename}.",
        "filename_placeholder": "filename",
    }


def test_build_chat_messages_renders_backend_supplied_templates() -> None:
    """Use the caller's roles and bindings, including literal braces."""
    templates = [SimpleChatMessage(role=MessageRole.ASSISTANT, content="{{example}} {value}")]
    messages = build_chat_messages(templates, {"value": "document {with braces}"})
    assert messages == [
        SimpleChatMessage(role=MessageRole.ASSISTANT, content="{example} document {with braces}")
    ]
    assert templates[0].content == "{{example}} {value}"


def test_build_chat_messages_reports_missing_binding() -> None:
    """Identify the missing placeholder and message role."""
    templates = [SimpleChatMessage(role=MessageRole.USER, content="{missing}")]
    with pytest.raises(
        MissingBindingError, match="No value for placeholder 'missing' in USER message"
    ) as raised:
        build_chat_messages(templates, {})
    assert raised.value.placeholder == "missing"
    assert raised.value.role == MessageRole.USER


@pytest.mark.parametrize(
    "template, fields",
    [
        ("{value!s}", {"value"}),
        ("{value[0]}", {"value"}),
        ("{value:{width}}", {"value", "width"}),
        ("{{value}} {{width}}", set()),
    ],
)
def test_get_template_placeholders_finds_bindings_without_interpreting_literals(template, fields):
    """Discover root bindings, including nested fields, using formatter syntax."""
    templates = [SimpleChatMessage(role=MessageRole.USER, content=template)]

    assert get_template_placeholders(templates) == fields


def test_prepare_template_request_renders_only_current_templates() -> None:
    """Use explicit binding values and leave already-rendered history alone."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous {turn}")]
    bindings = {"schema": "Custom schema text", "filename": "input.md"}
    templates = [
        SimpleChatMessage(role=MessageRole.SYSTEM, content="{schema}"),
        SimpleChatMessage(role=MessageRole.USER, content="Read {filename}."),
    ]

    request = prepare_template_request(templates, bindings=bindings, history=history)

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.SYSTEM, content="Custom schema text"),
        SimpleChatMessage(role=MessageRole.USER, content="Read input.md."),
    ]
    assert request.messages == [*history, *request.current_messages]
    assert request.input_artifacts == {}
    assert bindings == {"schema": "Custom schema text", "filename": "input.md"}
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous {turn}")]


@pytest.mark.parametrize("schema", [None, {"default": object()}], ids=["absent", "unused"])
def test_prepare_inline_request_can_omit_schema_bindings(schema) -> None:
    """Skip schema preparation when the template uses only the document."""
    request = prepare_inline_request(
        {
            "user_message": "{document} {{schema}} {{schema_description}}",
            "schema_description_kwargs": {"include_field_descriptions": False},
        },
        document="Source",
        schema=schema,
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="Source {schema} {schema_description}")
    ]


def test_prepare_inline_request_requires_a_template() -> None:
    """Fail before execution when neither message template is configured."""
    with pytest.raises(ValueError, match="At least one of system_message or user_message"):
        prepare_inline_request({}, document="Source", schema=None)


def test_prepare_inline_request_inserts_json_schema() -> None:
    """Render non-ASCII JSON Schema and Markdown from the built-in fields."""
    schema = {"type": "object", "properties": {"field": {"const": "Wälder"}}}
    request = prepare_inline_request(
        {"system_message": "{schema}", "user_message": "{document}"},
        document="Markdown",
        schema=schema,
    )

    system, user = request.messages
    assert json.loads(system.content) == schema
    assert "Wälder" in system.content
    assert user.content == "Markdown"


def test_prepare_inline_request_applies_schema_description_settings() -> None:
    """Pass the recognized formatting options through to the description builder."""
    schema = {
        "type": "object",
        "properties": {"field": {"type": "string", "description": "Field guidance"}},
    }
    request = prepare_inline_request(
        {
            "system_message": "{schema_description}",
            "user_message": "{document}",
            "schema_description_kwargs": {"include_field_descriptions": False},
        },
        document="Source",
        schema=schema,
    )

    system, _ = request.current_messages
    assert "field:" in system.content
    assert "Field guidance" not in system.content


@pytest.mark.parametrize("field", ["schema", "schema_description"])
def test_prepare_inline_request_requires_schema_for_referenced_field(field) -> None:
    """Name the field that requested the missing schema."""
    template = {"system_message": f"{{{field}}}", "user_message": "{document}"}
    with pytest.raises(ValueError, match=rf"\{{{field}\}}.*requires a schema"):
        prepare_inline_request(template, document="Markdown", schema=None)


def test_prepare_inline_request_rejects_legacy_alias() -> None:
    """A legacy alias is reported as an unknown field."""
    template = {
        "system_message": "{output_schema}",
        "user_message": "{document}",
    }
    with pytest.raises(MissingBindingError) as raised:
        prepare_inline_request(template, document="Markdown", schema={})

    assert raised.value.placeholder == "output_schema"
    assert raised.value.role == MessageRole.SYSTEM


def test_prepare_inline_request_reports_all_unrecognized_settings() -> None:
    """Reject legacy declarations even when the message uses built-in fields."""
    template = {
        "user_message": "{document}",
        "schema_placeholder": "schema_description",
        "document_placeholder": "document",
    }
    with pytest.raises(TypeError, match="'document_placeholder', 'schema_placeholder'"):
        prepare_inline_request(template, document="Source", schema=None)


@pytest.mark.parametrize(
    "user_message",
    ["Extract the fields.", "Extract from {{document}}."],
)
def test_prepare_inline_request_requires_document_in_first_turn(user_message) -> None:
    """Require a document field in the initial prompt."""
    with pytest.raises(ValueError, match=r"first inline turn must reference '\{document\}'"):
        prepare_inline_request({"user_message": user_message}, document="Markdown", schema=None)


def test_prepare_inline_request_keeps_history_separate_from_current_turn() -> None:
    """Allow a follow-up template without a document placeholder."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Markdown")]
    request = prepare_inline_request(
        {"user_message": "Extract one more field."},
        document="Markdown",
        schema=None,
        history=history,
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="Extract one more field.")
    ]
    assert request.messages == [*history, *request.current_messages]
    assert len(history) == 1
