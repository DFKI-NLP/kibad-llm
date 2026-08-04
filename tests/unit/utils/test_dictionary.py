from typing import Any

import pytest

from kibad_llm.utils.dictionary import flatten_to_value_lists


def test_wraps_flat_primitive_values_in_lists() -> None:
    data = {
        "string": "value",
        "integer": 2,
        "float": 1.5,
        "boolean": False,
    }

    assert flatten_to_value_lists(data) == {
        "string": ["value"],
        "integer": [2],
        "float": [1.5],
        "boolean": [False],
    }


def test_flattens_nested_mappings_with_custom_separator() -> None:
    data = {"study": {"location": {"country": "DE"}}}

    assert flatten_to_value_lists(data, sep="__") == {"study__location__country": ["DE"]}


def test_flattens_arbitrarily_nested_lists_and_preserves_duplicates() -> None:
    data = {"values": [3, [1, 3], [[2, 1]]]}

    assert flatten_to_value_lists(data) == {"values": [3, 1, 3, 2, 1]}


def test_aggregates_values_from_nested_mappings_in_lists() -> None:
    data = {
        "study": {
            "sites": [
                {
                    "country": "DE",
                    "taxa": [{"name": "Bee"}, {"name": "Ant"}],
                },
                {
                    "country": "AT",
                    "taxa": [[{"name": "Bee"}], {"name": "Wasp"}],
                },
            ]
        }
    }

    assert flatten_to_value_lists(data) == {
        "study.sites.country": ["DE", "AT"],
        "study.sites.taxa.name": ["Bee", "Ant", "Bee", "Wasp"],
    }


def test_accepts_a_top_level_sequence_of_mappings() -> None:
    data = (
        {"name": "first", "score": 2},
        {"name": "second", "score": 1},
    )

    assert flatten_to_value_lists(data) == {
        "name": ["first", "second"],
        "score": [2, 1],
    }


def test_sort_lists_applies_to_direct_and_aggregated_values() -> None:
    data = [
        {
            "direct": [3, 1, 3],
            "nested": [{"value": 3}, {"value": 1}],
        },
        {
            "direct": [2, 1],
            "nested": [{"value": 3}, {"value": 2}],
        },
    ]

    assert flatten_to_value_lists(data, sort_lists=True) == {
        "direct": [1, 1, 2, 3, 3],
        "nested.value": [1, 2, 3, 3],
    }


def test_omits_empty_values_and_containers() -> None:
    data: dict[str, Any] = {
        "none": None,
        "empty": "",
        "blank": "  \t",
        "empty_list": [],
        "empty_mapping": {},
        "nested": [None, " ", [], {}],
        "retained": [0, False, "value"],
    }

    assert flatten_to_value_lists(data) == {"retained": [0, False, "value"]}


def test_rejects_non_string_keys_in_nested_mappings() -> None:
    with pytest.raises(
        TypeError,
        match="Expected a string key at 'nested', got int",
    ):
        flatten_to_value_lists({"nested": {1: "value"}})  # type: ignore[dict-item]


def test_rejects_unsupported_nested_values_with_their_path() -> None:
    with pytest.raises(
        TypeError,
        match="Unsupported value of type tuple at 'nested.value'",
    ):
        flatten_to_value_lists({"nested": {"value": (1, 2)}})
