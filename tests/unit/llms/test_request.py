"""Tests for prompt rendering and default request preparation."""

import json

from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.llms.request import (
    ExtractionPrompt,
    MissingBindingError,
    SimpleChatMessage,
    build_chat_messages,
    prepare_inline_request,
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


def test_prepare_template_request_renders_schema_and_preserves_caller_inputs() -> None:
    """Render a file-oriented prompt with custom bindings and unchanged history."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    bindings = {"filename": "input.md"}
    schema = {"type": "object", "properties": {"habitat": {"type": "string"}}}
    prompt = ExtractionPrompt(
        document="Original Markdown",
        schema=schema,
        system_message="{description}",
        user_message="Read {filename}; {{markdown}} is literal.\n{output_schema}",
        history=history,
        document_placeholder="markdown",
        schema_placeholder="output_schema",
        schema_description_placeholder="description",
    )

    request = prepare_template_request(prompt, bindings=bindings)

    system, user = request.current_messages
    assert system.role == MessageRole.SYSTEM
    assert "habitat" in system.content
    assert user.role == MessageRole.USER
    assert user.content.startswith("Read input.md; {markdown} is literal.\n")
    assert json.loads(user.content.split("\n", maxsplit=1)[1]) == schema
    assert request.messages == [*history, system, user]
    assert request.input_artifacts == {}
    assert all(prompt.document not in message.content for message in request.messages)
    assert bindings == {"filename": "input.md"}
    assert history == [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    assert prompt.user_message == "Read {filename}; {{markdown}} is literal.\n{output_schema}"


def test_prepare_template_request_requires_explicit_document_binding() -> None:
    """Leave document binding to the caller even when the source document is available."""
    prompt = ExtractionPrompt(document="Source", schema=None, user_message="Read {document}")

    with pytest.raises(MissingBindingError) as raised:
        prepare_template_request(prompt, bindings={})

    assert raised.value.placeholder == "document"
    assert raised.value.role == MessageRole.USER


@pytest.mark.parametrize("placeholder", ["output_schema", "description"])
def test_prepare_template_request_rejects_schema_binding_overrides(placeholder: str) -> None:
    """Reject caller bindings that collide with either configured schema placeholder."""
    prompt = ExtractionPrompt(
        document="Source",
        schema={},
        user_message="{output_schema}",
        schema_placeholder="output_schema",
        schema_description_placeholder="description",
    )

    with pytest.raises(ValueError, match="must not override schema placeholders"):
        prepare_template_request(prompt, bindings={placeholder: "Replacement"})


def test_prepare_template_request_warns_about_unused_schema_without_rendering_it(
    monkeypatch,
) -> None:
    """Treat escaped schema fields as literals even when the caller supplies bindings."""
    warnings: list[str] = []
    monkeypatch.setattr("kibad_llm.llms.request.warn_once", warnings.append)
    prompt = ExtractionPrompt(
        document="Source",
        schema={"default": object()},
        user_message="{filename} {{schema}} {{schema_description}}",
    )

    request = prepare_template_request(prompt, bindings={"filename": "input.md"})

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="input.md {schema} {schema_description}")
    ]
    assert len(warnings) == 1
    assert warnings[0].startswith(
        "Schema provided but message templates use neither schema placeholder"
    )


@pytest.mark.parametrize("placeholder", ["schema", "schema_description"])
def test_prepare_template_request_requires_referenced_schema(placeholder: str) -> None:
    """Require a schema for both schema representations in file-oriented templates."""
    prompt = ExtractionPrompt(document="Source", schema=None, user_message="{" + placeholder + "}")

    with pytest.raises(ValueError, match="Schema must be provided"):
        prepare_template_request(prompt, bindings={})


def test_prepare_template_request_requires_a_template() -> None:
    """Fail before execution when neither message template is configured."""
    with pytest.raises(ValueError, match="At least one of system_message or user_message"):
        prepare_template_request(ExtractionPrompt(document="Source", schema=None), bindings={})


def test_prepare_inline_request_inserts_json_schema_with_custom_placeholder(monkeypatch) -> None:
    """Render non-ASCII JSON Schema and Markdown using the configured placeholder names."""
    schema = {"type": "object", "properties": {"field": {"const": "Wälder"}}}
    warnings: list[str] = []
    monkeypatch.setattr("kibad_llm.llms.request.warn_once", warnings.append)
    request = prepare_inline_request(
        ExtractionPrompt(
            system_message="{output_schema}",
            user_message="{markdown}",
            document="Markdown",
            document_placeholder="markdown",
            schema=schema,
            schema_placeholder="output_schema",
        )
    )

    system, user = request.messages
    assert json.loads(system.content) == schema
    assert "Wälder" in system.content
    assert user.content == "Markdown"
    assert warnings == []


def test_prepare_inline_request_rejects_missing_json_schema() -> None:
    """Require a schema when a template references it."""
    with pytest.raises(ValueError, match="requires JSON Schema"):
        prepare_inline_request(
            ExtractionPrompt(system_message="{schema}", document="Markdown", schema=None)
        )


@pytest.mark.parametrize("user_message", ["Extract the fields.", "Extract from {{document}}."])
def test_prepare_inline_request_requires_document_in_first_turn(user_message: str) -> None:
    """Require an actual document binding in an initial prompt."""
    with pytest.raises(ValueError, match="must contain"):
        prepare_inline_request(
            ExtractionPrompt(user_message=user_message, document="Markdown", schema=None)
        )


def test_prepare_inline_request_keeps_history_separate_from_current_turn() -> None:
    """Allow a follow-up template without a document placeholder."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Markdown")]
    request = prepare_inline_request(
        ExtractionPrompt(
            user_message="Extract one more field.",
            document="Markdown",
            schema=None,
            history=history,
        )
    )

    assert request.current_messages == [
        SimpleChatMessage(role=MessageRole.USER, content="Extract one more field.")
    ]
    assert request.messages == [*history, *request.current_messages]
    assert len(history) == 1
