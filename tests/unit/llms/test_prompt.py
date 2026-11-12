"""Tests for prompt rendering and default request preparation."""

import json

from llama_index.core.base.llms.types import MessageRole
import pytest

from kibad_llm.llms.prompt import (
    ExtractionPrompt,
    SimpleChatMessage,
    build_chat_messages,
    prepare_inline_request,
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
    with pytest.raises(ValueError, match="No value for placeholder 'missing' in USER message"):
        build_chat_messages(templates, {})


def test_prepare_inline_request_inserts_json_schema_with_custom_placeholder(monkeypatch) -> None:
    """Render non-ASCII JSON Schema and Markdown using the configured placeholder names."""
    schema = {"type": "object", "properties": {"field": {"const": "Wälder"}}}
    warnings: list[str] = []
    monkeypatch.setattr("kibad_llm.llms.prompt.warn_once", warnings.append)
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
