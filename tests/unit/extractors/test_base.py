import copy

import pytest

from kibad_llm.extractors.base import (
    _find_anchor_match_spans,
    check_utf8_encodable,
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


TEXT = (
    "Results\n\nIn mixed stands, _Fagus sylvatica_ showed higher above-ground productivity.\n"
    "Several unrelated sentences follow here. Decomposition was \u201cfaster\u201d in pure stands."
)


@pytest.mark.parametrize(
    "anchor, expected",
    [
        # verbatim, wrapping quotes, and different whitespace
        ("higher above-ground productivity", "higher above-ground productivity"),
        ('"higher above-ground\n productivity"', "higher above-ground productivity"),
    ],
)
def test_find_anchor_match_spans_matches_verbatim_variants(anchor, expected) -> None:
    spans = _find_anchor_match_spans(TEXT, anchor)
    assert [TEXT[start:end] for start, end in spans] == [expected]


def test_find_anchor_match_spans_prefers_exact_over_lenient_matches() -> None:
    text = "Mixed stands. mixed stands."
    assert _find_anchor_match_spans(text, "mixed stands") == [(14, 26)]


@pytest.mark.parametrize("anchor", ["", "  ", "\u2026", "lower productivity", "**"])
def test_find_anchor_match_spans_without_match(anchor) -> None:
    assert _find_anchor_match_spans(TEXT, anchor) == []
