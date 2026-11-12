import copy
from dataclasses import replace
import json

from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole
import pytest

from kibad_llm.extractors.base import (
    check_utf8_encodable,
    extract_from_text,
    strip_metadata,
)
from kibad_llm.llms.base import LLM
from kibad_llm.llms.prompt import ExtractionPrompt, PreparedRequest, SimpleChatMessage


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

        def prepare_request(self, prompt: ExtractionPrompt) -> PreparedRequest:
            """Use the sliced document to render a backend-specific template."""
            assert prompt.document == "document"
            request = super().prepare_request(replace(prompt, user_message="Backend: {document}"))
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
