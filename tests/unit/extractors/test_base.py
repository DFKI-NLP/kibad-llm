import copy
import json
from types import SimpleNamespace

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole
import pytest

from kibad_llm.extractors.base import (
    check_utf8_encodable,
    extract_from_text,
    strip_metadata,
)
from kibad_llm.llms.base import LLM
from kibad_llm.llms.request import PreparedRequest, SimpleChatMessage


def test_strip_metadata_unwraps_simple_wrapper() -> None:
    data = {"name": {"content": "Alice", "evidence_anchor": "…"}}
    out = strip_metadata(data, content_key="content")
    assert out == {"name": "Alice"}


def test_strip_metadata_unwraps_nested_wrappers_in_objects_and_lists() -> None:
    data = {
        "obj": {
            "x": {"content": 1, "evidence_anchor": "quote"},
            "y": [
                {"content": "a", "evidence_anchor": "q1"},
                {"content": "b", "evidence_anchor": "q2"},
            ],
        }
    }
    out = strip_metadata(data, content_key="content")
    assert out == {"obj": {"x": 1, "y": ["a", "b"]}}


def test_strip_metadata_handles_nullable_union_shape() -> None:
    # Typical output shape when schema allowed null OR wrapped value:
    # anyOf is schema-side; runtime data is either None or the wrapper object.
    data = {"maybe": None, "maybe2": {"content": "x", "evidence_anchor": "…"}}
    out = strip_metadata(data, content_key="content")
    assert out == {"maybe": None, "maybe2": "x"}


def test_strip_metadata_does_not_unwrap_plain_content_only_object() -> None:
    # Heuristic: wrapper must have content_key AND at least one additional key.
    data = {"note": {"content": "keep_me"}}
    out = strip_metadata(data, content_key="content")
    assert out == {"note": {"content": "keep_me"}}


def test_strip_metadata_is_pure_does_not_mutate_input() -> None:
    data = {
        "name": {"content": "Alice", "evidence_anchor": "…"},
        "tags": [{"content": "x", "evidence_anchor": "q"}],
    }
    before = copy.deepcopy(data)
    _ = strip_metadata(data, content_key="content")
    assert data == before


def test_strip_metadata_custom_content_key() -> None:
    data = {"name": {"value": "Alice", "evidence_anchor": "…"}}
    out = strip_metadata(data, content_key="value")
    assert out == {"name": "Alice"}


def test_check_utf8_encodable_passes_for_well_formed_data() -> None:
    data = {
        "response_content": "some ordinary text, including umlauts like ä ö ü",
        "structured": {"habitat": "Wald", "species": ["Rotfuchs", "Wildschwein"]},
        "errors": [],
    }
    # should not raise
    check_utf8_encodable(data)


def test_check_utf8_encodable_raises_for_lone_surrogate_in_plain_string() -> None:
    with pytest.raises(UnicodeEncodeError) as excinfo:
        check_utf8_encodable("some text with a lone surrogate \udd7a in it")
    assert str(excinfo.value) == (
        "'utf-8' codec can't encode character '\\udd7a' in position 32: surrogates "
        "not allowed (string: 'some text with a lone surrogate \\udd7a in it')"
    )


def test_check_utf8_encodable_raises_for_lone_surrogate_nested_in_dict_and_list() -> None:
    data = {
        "structured": {
            "habitat": "Wald",
            "species": ["Rotfuchs", "Wild\udd7aschwein"],
        }
    }
    with pytest.raises(UnicodeEncodeError) as excinfo:
        check_utf8_encodable(data)

    assert str(excinfo.value) == (
        "'utf-8' codec can't encode character '\\udd7a' in position 4: surrogates "
        "not allowed (string: 'Wild\\udd7aschwein')"
    )


def test_backend_prepares_messages_before_extractor_records_them() -> None:
    """Send the full backend-prepared request and record only its current turn."""
    history = [SimpleChatMessage(role=MessageRole.USER, content="Previous turn")]
    prepared_user = SimpleChatMessage(role=MessageRole.USER, content="Backend: document")

    class TestLLM(LLM):
        """Customize the prompt and provide an auxiliary input to the chat call."""

        def prepare_request(
            self, prompt_template, *, document, schema, history=()
        ) -> PreparedRequest:
            """Use the sliced document to render a backend-specific template."""
            assert document == "document"
            request = super().prepare_request(
                {**prompt_template, "user_message": "Backend: {document}"},
                document=document,
                schema=schema,
                history=history,
            )
            request.input_artifacts["context.txt"] = "Extra context"
            return request

        def call_llm_chat_with_guided_decoding(
            self, messages, *, json_schema=None, **request_kwargs
        ) -> ChatResponse:
            """Check the prepared request received by the backend."""
            assert messages == [*history, prepared_user]
            assert json_schema is None
            assert request_kwargs == {
                "seed": 42,
                "input_artifacts": {"context.txt": "Extra context"},
            }
            return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content="{}"))

    request_parameters = {"seed": 42}
    result = extract_from_text(
        text="a document",
        text_id="fixture",
        character_start=2,
        prompt_template={"user_message": "Configured: {document}"},
        history=history,
        llm=TestLLM(),
        use_guided_decoding=False,
        request_parameters=request_parameters,
        return_messages=True,
        return_messages_formatted=True,
        truncate_user_message_formatted=7,
    )

    assert result.errors == []
    assert result.backend_metadata is None
    assert result.structured == {}
    assert result.messages == {"system": None, "user": "Configured: {document}"}
    assert result.messages_formatted == {"user": "Backend... (truncated @ 7 chars)"}
    assert request_parameters == {"seed": 42}


@pytest.mark.parametrize("use_wrapped_schema", [False, True])
def test_extract_from_text_uses_same_schema_for_both_placeholders(
    use_wrapped_schema: bool,
) -> None:
    schema = {
        "type": "object",
        "properties": {"habitat": {"type": "string", "description": "Habitat label"}},
    }
    result = extract_from_text(
        text="A forest.",
        text_id="fixture",
        prompt_template={
            "system_message": "{schema_description}",
            "user_message": "{document}\n{schema}",
            "schema_description_placeholder": "schema_description",
            "schema_placeholder": "schema",
        },
        schema=schema,
        adjust_schema_for_evidence_detection=True,
        adjust_schema_description_for_evidence_detection=use_wrapped_schema,
        return_messages=True,
        return_messages_formatted=True,
        truncate_user_message_formatted=None,
    )

    assert result.backend_metadata is None
    assert result.messages == {
        "system": "{schema_description}",
        "user": "{document}\n{schema}",
    }
    assert result.messages_formatted is not None
    assert "Habitat label" in result.messages_formatted["system"]
    assert ("evidence_anchor" in result.messages_formatted["system"]) == use_wrapped_schema
    document, rendered_schema = result.messages_formatted["user"].split("\n", maxsplit=1)
    assert document == "A forest."
    rendered = json.loads(rendered_schema)
    if use_wrapped_schema:
        assert set(rendered["properties"]["habitat"]["properties"]) == {
            "content",
            "evidence_anchor",
        }
    else:
        assert rendered == schema


@pytest.mark.parametrize(
    ("content", "return_reasoning", "validate_with_schema", "expected_error"),
    [
        ("{}", False, False, None),
        (None, False, False, "MissingResponseContentError"),
        ("", False, False, "EmptyResponseMessageError"),
        ("invalid json", False, False, "JSONDecodeError"),
        ("{}", False, True, "ValidationError"),
        ("{}", True, False, "NotImplementedError"),
    ],
)
def test_backend_metadata_survives_postprocessing_errors(
    content, return_reasoning: bool, validate_with_schema: bool, expected_error
) -> None:
    """Retain usage for responses that cannot produce a valid extraction."""
    usage = {"input_tokens": 120, "output_tokens": 30, "total_tokens": 150}

    class TestLLM(LLM):
        """Return usage independently of the response's parseable content."""

        def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
            """Return the test response without contacting a backend."""
            return ChatResponse(
                message=ChatMessage(content=content), raw=SimpleNamespace(usage=usage)
            )

    result = extract_from_text(
        text="document",
        text_id="test",
        prompt_template={"user_message": "{document}"},
        schema={"type": "object", "required": ["missing"]},
        use_guided_decoding=False,
        validate_with_schema=validate_with_schema,
        return_reasoning=return_reasoning,
        llm=TestLLM(),
    )

    assert result.backend_metadata == {"usage": usage}
    if expected_error is None:
        assert result.errors == []
    else:
        assert any(error.startswith(expected_error + ":") for error in result.errors)


def test_metadata_error_does_not_discard_structured_output() -> None:
    """Report malformed backend usage through the existing extraction error fields."""

    class TestLLM(LLM):
        """Return valid content with invalid usage metadata."""

        def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
            """Provide a response that fails only the metadata callback."""
            return ChatResponse(message=ChatMessage(content="{}"), raw={"usage": "invalid"})

    result = extract_from_text(
        text="document",
        text_id="test",
        prompt_template={"user_message": "{document}"},
        use_guided_decoding=False,
        llm=TestLLM(),
    )
    assert result.backend_metadata is None
    assert result.structured == {}
    assert len(result.errors) == 1
    assert result.errors[0].startswith("TypeError: Unsupported token usage type")
