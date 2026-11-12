import copy
import json

import pytest

from kibad_llm.extractors.base import (
    build_chat_messages,
    check_utf8_encodable,
    extract_from_text,
    strip_metadata,
)


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


def test_build_chat_messages_inserts_json_schema_with_custom_placeholder(monkeypatch) -> None:
    schema = {"type": "object", "properties": {"field": {"const": "Wälder"}}}
    warnings: list[str] = []
    monkeypatch.setattr("kibad_llm.extractors.base.warn_once", warnings.append)

    system, user = build_chat_messages(
        system_message="{output_schema}",
        user_message="{document}",
        document="Markdown",
        schema=schema,
        schema_placeholder="output_schema",
    )

    assert json.loads(system.content) == schema
    assert "Wälder" in system.content
    assert user.content == "Markdown"
    assert warnings == []


def test_build_chat_messages_rejects_missing_json_schema() -> None:
    with pytest.raises(ValueError, match="requires JSON Schema"):
        build_chat_messages(
            system_message="{schema}", user_message="{document}", document="Markdown"
        )


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
