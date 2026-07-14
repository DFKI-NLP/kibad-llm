import copy

import pytest

from kibad_llm.extractors.base import (
    LoneSurrogateError,
    check_no_lone_surrogates,
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


def test_check_no_lone_surrogates_passes_for_well_formed_data() -> None:
    data = {
        "response_content": "some ordinary text, including umlauts like ä ö ü",
        "structured": {"habitat": "Wald", "species": ["Rotfuchs", "Wildschwein"]},
        "errors": [],
    }
    # should not raise
    check_no_lone_surrogates(data)


def test_check_no_lone_surrogates_raises_for_lone_surrogate_in_plain_string() -> None:
    with pytest.raises(LoneSurrogateError):
        check_no_lone_surrogates("some text with a lone surrogate \udd7a in it")


def test_check_no_lone_surrogates_raises_for_lone_surrogate_nested_in_dict_and_list() -> None:
    data = {
        "structured": {
            "habitat": "Wald",
            "species": ["Rotfuchs", "Wild\udd7aschwein"],
        }
    }
    with pytest.raises(LoneSurrogateError):
        check_no_lone_surrogates(data)


def test_check_no_lone_surrogates_error_message_contains_truncated_repr() -> None:
    bad_string = "x" * 3000 + "\udd7a"
    with pytest.raises(LoneSurrogateError) as excinfo:
        check_no_lone_surrogates(bad_string)
    message = str(excinfo.value)
    assert "data=" in message
    # the full 3000+ character string should not be dumped into the message
    assert len(message) < 2000
