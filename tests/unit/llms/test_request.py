"""Tests for prompt rendering and default request preparation."""

from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.llms.base import prepare_request
from kibad_llm.llms.request import (
    MissingBindingError,
    SimpleChatMessage,
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
    original = prompt_template.copy()

    templates, remaining_settings = get_message_templates(prompt_template)

    assert templates == [SimpleChatMessage(role=MessageRole.USER, content="Read {filename}.")]
    assert remaining_settings == {"filename_placeholder": "filename"}
    assert prompt_template == original


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
    """Render the current turn with literal braces and keep history as supplied."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous {turn}")]
    templates = [
        SimpleChatMessage(role=MessageRole.SYSTEM, content="System instructions"),
        SimpleChatMessage(role=MessageRole.ASSISTANT, content="{{example}} {value}"),
    ]

    request = prepare_template_request(
        templates, bindings={"value": "document {with braces}"}, history=history
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.SYSTEM, content="System instructions"),
        SimpleChatMessage(role=MessageRole.ASSISTANT, content="{example} document {with braces}"),
    ]
    assert request.messages == [*history, *request.current_messages]
    assert request.input_artifacts == {}
    assert templates[1].content == "{{example}} {value}"
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous {turn}")]


@pytest.mark.parametrize("schema", [None, {"default": object()}], ids=["absent", "unused"])
def test_prepare_request_can_omit_schema_bindings(schema) -> None:
    """Skip schema preparation when the template uses only the document."""
    request = prepare_request(
        {"user_message": "{document} {{schema}} {{schema_description}}"},
        document="Source",
        schema=schema,
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="Source {schema} {schema_description}")
    ]


def test_prepare_request_requires_a_template() -> None:
    """Fail before execution when neither message template is configured."""
    with pytest.raises(ValueError, match="At least one of system_message or user_message"):
        prepare_request({}, document="Source", schema=None)


def test_prepare_request_applies_schema_description_settings() -> None:
    """Pass the recognized formatting options through to the description builder."""
    schema = {
        "type": "object",
        "properties": {"field": {"type": "string", "description": "Field guidance"}},
    }
    request = prepare_request(
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
def test_prepare_request_requires_schema_for_referenced_field(field) -> None:
    """Name the field that requested the missing schema."""
    template = {"system_message": f"{{{field}}}", "user_message": "{document}"}
    with pytest.raises(ValueError, match=rf"\{{{field}\}}.*requires a schema"):
        prepare_request(template, document="Markdown", schema=None)


def test_prepare_request_reports_unknown_field() -> None:
    """Identify the unknown field and the message referencing it."""
    template = {"system_message": "{output_schema}", "user_message": "{document}"}
    with pytest.raises(MissingBindingError, match="output_schema.*SYSTEM") as raised:
        prepare_request(template, document="Markdown", schema={})

    assert raised.value.placeholder == "output_schema"
    assert raised.value.role == MessageRole.SYSTEM


@pytest.mark.parametrize(
    "user_message",
    ["Extract the fields.", "Extract from {{document}}."],
)
def test_prepare_request_requires_document_in_first_turn(user_message) -> None:
    """Require a document field in the initial prompt."""
    with pytest.raises(ValueError, match=r"first inline turn must reference '\{document\}'"):
        prepare_request({"user_message": user_message}, document="Markdown", schema=None)


def test_prepare_request_keeps_history_separate_from_current_turn() -> None:
    """Allow a follow-up template without a document placeholder."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Markdown")]
    request = prepare_request(
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
