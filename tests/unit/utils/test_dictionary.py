import re
from typing import Any

import pytest

from kibad_llm.utils.dictionary import flatten_to_value_lists


def test_wraps_scalar_leaf_values_in_lists() -> None:
    assert flatten_to_value_lists(
        {
            "string": "value",
            "integer": 2,
            "float": 1.5,
            "boolean": False,
            "none": None,
        }
    ) == {
        "string": ["value"],
        "integer": [2],
        "float": [1.5],
        "boolean": [False],
        "none": [None],
    }


def test_flattens_nested_structures_in_depth_first_order() -> None:
    data = {
        "values": [3, [1, 3], [[2, 1]]],
        "sites": [
            {
                "country": "DE",
                "taxa": [{"name": "Bee"}, {"name": "Ant"}],
            },
            {
                "country": "AT",
                "taxa": [[{"name": "Bee"}], {"name": "Wasp"}],
            },
        ],
    }

    assert flatten_to_value_lists(data) == {
        "values": [3, 1, 3, 2, 1],
        "sites.country": ["DE", "AT"],
        "sites.taxa.name": ["Bee", "Ant", "Bee", "Wasp"],
    }


def test_aggregates_top_level_dictionaries_and_sorts_all_lists() -> None:
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


@pytest.mark.parametrize(
    ("remove_empty_values", "expected"),
    [
        (
            False,
            {
                "values": [None, "", " \t", " value ", 0, False],
                "only_empty_values": [None, "", " \t"],
            },
        ),
        (True, {"values": [" value ", 0, False]}),
    ],
)
def test_optional_empty_value_removal(
    remove_empty_values: bool,
    expected: dict[str, list[Any]],
) -> None:
    data: dict[str, Any] = {
        "values": [None, "", " \t", " value ", 0, False],
        "only_empty_values": [None, "", " \t"],
        "empty_list": [],
        "empty_dictionary": {},
        "nested_empty_containers": [[[]], [{}]],
    }

    assert (
        flatten_to_value_lists(
            data,
            remove_empty_values=remove_empty_values,
        )
        == expected
    )


def test_supports_custom_separator_and_empty_keys() -> None:
    data = {
        "a": {"": 2, "b": {"c": 3}},
        "": {"": 4},
    }

    assert flatten_to_value_lists(data, sep="__") == {
        "a__": [2],
        "a__b__c": [3],
        "__": [4],
    }


@pytest.mark.parametrize(
    ("data", "sep", "message"),
    [
        ({"a": 1}, "", "sep must not be empty"),
        (
            {"a": {"b.c": 2}},
            ".",
            "Key 'b.c' at 'a' contains the separator '.'",
        ),
    ],
)
def test_rejects_invalid_separators(
    data: dict[str, Any],
    sep: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(message)):
        flatten_to_value_lists(data, sep=sep)


@pytest.mark.parametrize(
    ("data", "kwargs", "message"),
    [
        (
            {"nested": {1: "value"}},
            {},
            "Expected a string key at 'nested', got int",
        ),
        (
            {"nested": {"value": (1, 2)}},
            {},
            "Unsupported value of type tuple at 'nested.value'",
        ),
        (
            {"values": [1, "value"]},
            {"sort_lists": True},
            "not supported between instances",
        ),
    ],
    ids=["non-string-key", "unsupported-value", "incomparable-values"],
)
def test_rejects_invalid_nested_data(
    data: dict[str, Any],
    kwargs: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(TypeError, match=re.escape(message)):
        flatten_to_value_lists(data, **kwargs)
