"""Tests for prompt rendering and default request preparation."""

import json

from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.llms.base import prepare_inline_request
from kibad_llm.llms.request import (
    MissingBindingError,
    SimpleChatMessage,
    build_chat_messages,
    get_template_placeholders,
    prepare_template_request,
)


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


def test_prepare_inline_request_can_omit_schema_bindings() -> None:
    """Leave a supplied schema alone when the template uses only the document."""
    request = prepare_inline_request(
        {
            "user_message": "{document} {{schema}} {{schema_description}}",
            "document_placeholder": "document",
            "schema_placeholder": "schema",
            "schema_description_placeholder": "schema_description",
        },
        document="Source",
        schema={"default": object()},
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="Source {schema} {schema_description}")
    ]


def test_prepare_inline_request_requires_a_template() -> None:
    """Fail before execution when neither message template is configured."""
    with pytest.raises(ValueError, match="At least one of system_message or user_message"):
        prepare_inline_request({}, document="Source", schema=None)


def test_prepare_inline_request_inserts_json_schema_with_custom_placeholder() -> None:
    """Render non-ASCII JSON Schema and Markdown using the configured placeholder names."""
    schema = {"type": "object", "properties": {"field": {"const": "Wälder"}}}
    request = prepare_inline_request(
        {
            "system_message": "{output_schema}",
            "user_message": "{markdown}",
            "document_placeholder": "markdown",
            "schema_placeholder": "output_schema",
        },
        document="Markdown",
        schema=schema,
    )

    system, user = request.messages
    assert json.loads(system.content) == schema
    assert "Wälder" in system.content
    assert user.content == "Markdown"


@pytest.mark.parametrize("placeholder", ["schema", "schema_description"])
@pytest.mark.parametrize("schema", [None, {}], ids=["no-schema", "undeclared-field"])
def test_prepare_inline_request_reports_missing_schema_binding(placeholder, schema) -> None:
    """A referenced schema field requires both a declaration and a schema."""
    template = {
        "system_message": f"{{{placeholder}}}",
        "user_message": "{document}",
        "document_placeholder": "document",
    }
    if schema is None:
        template[f"{placeholder}_placeholder"] = placeholder
    with pytest.raises(MissingBindingError) as raised:
        prepare_inline_request(template, document="Markdown", schema=schema)

    assert raised.value.placeholder == placeholder
    assert raised.value.role == MessageRole.SYSTEM


@pytest.mark.parametrize(
    "template",
    [
        {"user_message": "Extract the fields."},
        {"user_message": "Extract the fields.", "document_placeholder": "document"},
        {"user_message": "Extract from {{document}}.", "document_placeholder": "document"},
    ],
)
def test_prepare_inline_request_requires_document_in_first_turn(template) -> None:
    """Require a declared and referenced document field in the initial prompt."""
    with pytest.raises(ValueError, match="first inline turn must declare 'document_placeholder'"):
        prepare_inline_request(template, document="Markdown", schema=None)


def test_prepare_inline_request_reports_undeclared_document_field() -> None:
    """Using the conventional field name still requires a declaration."""
    with pytest.raises(MissingBindingError) as raised:
        prepare_inline_request({"user_message": "{document}"}, document="Markdown", schema=None)
    assert raised.value.placeholder == "document"
    assert raised.value.role == MessageRole.USER


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
