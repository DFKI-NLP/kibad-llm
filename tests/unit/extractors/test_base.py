import copy
import json
from types import SimpleNamespace
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole
import pytest

from kibad_llm.extractors.base import (
    check_utf8_encodable,
    extract_from_text,
    strip_metadata,
)
from kibad_llm.llms.base import LLM
from kibad_llm.llms.request import PreparedRequest, SimpleChatMessage


def test_strip_metadata_unwraps_nested_wrappers_in_objects_and_lists() -> None:
    """Unwrap nested values while preserving plain objects, nulls, and the input."""
    data = {
        "observation": {
            "count": {"content": 2, "evidence_anchor": "two oaks"},
            "species": [{"content": "oak", "evidence_anchor": "oaks"}, None],
            "note": {"content": "mixed forest"},
        },
    }
    before = copy.deepcopy(data)

    assert strip_metadata(data, content_key="content") == {
        "observation": {"count": 2, "species": ["oak", None], "note": {"content": "mixed forest"}},
    }
    assert data == before


def test_strip_metadata_custom_content_key() -> None:
    """Use the selected key to recognize and unwrap a metadata wrapper."""
    data = {"name": {"value": "Alice", "evidence_anchor": "…"}}
    assert strip_metadata(data, content_key="value") == {"name": "Alice"}


def test_check_utf8_encodable_accepts_unicode() -> None:
    """Accept well-formed Unicode in nested results."""
    check_utf8_encodable({"species": ["Eichhörnchen"]})


def test_check_utf8_encodable_reports_nested_surrogate() -> None:
    """Identify the offending string when encoding a nested result fails."""
    invalid_name = "Wild\udd7aschwein"
    with pytest.raises(UnicodeEncodeError) as error:
        check_utf8_encodable({"species": ["Rotfuchs", invalid_name]})
    assert repr(invalid_name) in error.value.reason


@pytest.mark.parametrize("key", ["system_message", "user_message", "schema_description_kwargs"])
def test_extract_from_text_rejects_top_level_prompt_settings(key: str) -> None:
    """Require prompt settings to be supplied inside the prompt template mapping."""
    unexpected_setting: dict[str, Any] = {key: None}
    with pytest.raises(TypeError, match=f"unexpected keyword argument '{key}'"):
        extract_from_text(
            text="A forest.",
            text_id="fixture",
            prompt_template={"user_message": "{document}"},
            use_guided_decoding=False,
            **unexpected_setting,
        )


def test_extract_from_text_reports_unrecognized_inline_prompt_settings() -> None:
    """Name both the misspelled option and the retired placeholder declaration."""
    with pytest.raises(TypeError) as error:
        extract_from_text(
            text="A forest.",
            text_id="fixture",
            prompt_template={
                "system_message": "{schema_description}",
                "user_message": "{document}",
                "schema_placeholder": "schema_description",
                "schema_description_kwarg": {"include_field_descriptions": False},
            },
            schema={"type": "object"},
        )
    assert "'schema_description_kwarg'" in str(error.value)
    assert "'schema_placeholder'" in str(error.value)


def test_backend_prepares_messages_before_extractor_records_them() -> None:
    """Send the full backend-prepared request and record only its current turn."""
    history = [SimpleChatMessage(role=MessageRole.ASSISTANT, content="Previous turn")]
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
        prompt_template={
            "user_message": "Configured: {document}",
        },
        history=history,
        llm=TestLLM(),
        use_guided_decoding=False,
        request_parameters=request_parameters,
        return_messages=True,
        return_messages_formatted=True,
        truncate_user_message_formatted=7,
    )

    assert result.errors == []
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
        },
        schema=schema,
        adjust_schema_for_evidence_detection=True,
        adjust_schema_description_for_evidence_detection=use_wrapped_schema,
        return_messages=True,
        return_messages_formatted=True,
        truncate_user_message_formatted=None,
    )

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
