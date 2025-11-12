import pytest

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet


def test_prepare_entry_as_set_single_value():
    m = MetricWithPrepareEntryAsSet()
    assert m._prepare_entry_as_set(None) == set()
    # simple scalar
    assert m._prepare_entry_as_set("x") == {"x"}
    # simple dict: sorts and removes None
    assert m._prepare_entry_as_set({"b": 2, "a": 1, "c": None}) == {(("a", 1), ("b", 2))}
    # tuple: does not sort and keeps None
    assert m._prepare_entry_as_set(("b", "a", None)) == {("b", "a", None)}
    # dict with list non-hashable value
    with pytest.raises(TypeError):
        assert m._prepare_entry_as_set({"labels": ["a"]})


def test_prepare_entry_as_set_multi_value():
    m = MetricWithPrepareEntryAsSet()
    # list with duplicates and None
    assert m._prepare_entry_as_set(["a", "a", "b", None]) == {"a", "b"}
    # set with None
    assert m._prepare_entry_as_set({"a", "b", None, "a"}) == {"a", "b"}
    # list with dict entries and Nones
    assert m._prepare_entry_as_set([{"a": 1}, {"b": 2, "c": 3, "d": None}, None]) == {
        (("a", 1),),
        (("b", 2), ("c", 3)),
    }


def test_prepare_entry_as_set_with_list_of_dicts():
    m = MetricWithPrepareEntryAsSet()
    input_data = [{"key1": "value1"}, {"key2": "value2"}, {"key1": "value1"}]
    expected_output = {(("key1", "value1"),), (("key2", "value2"),)}
    assert m._prepare_entry_as_set(input_data) == expected_output

    # mixed type entries with duplicates and None
    input_data_mixed = [
        {"key1": "value1"},
        "simple_value",
        {"key2": "value2"},
        None,
        None,
        "simple_value",
    ]
    expected_output_mixed = {(("key1", "value1"),), "simple_value", (("key2", "value2"),)}
    assert m._prepare_entry_as_set(input_data_mixed) == expected_output_mixed


def test_prepare_entry_as_set_with_field():
    m = MetricWithPrepareEntryAsSet(field="labels")
    assert m._prepare_entry_as_set({"labels": ["x", "y", "y"]}) == {"x", "y"}
    assert m._prepare_entry_as_set({"other": "z"}) == set()
    assert m._prepare_entry_as_set({"labels": None}) == set()


def test_prepare_entry_as_set_with_field_no_dict():
    m = MetricWithPrepareEntryAsSet(field="labels")
    with pytest.raises(ValueError) as excinfo:
        m._prepare_entry_as_set("no_dict")
    assert (
        str(excinfo.value)
        == "Expected entry to be a dict when field is set, but got <class 'str'>"
    )


def test_prepare_entry_as_set_with_field_and_ignore_subfields():
    m = MetricWithPrepareEntryAsSet(field="items", ignore_subfields={"items": ["ignore_me"]})
    input_data = {
        "items": [
            {"key1": "value1", "ignore_me": "foo"},
            {"key2": "value2", "ignore_me": "bar"},
            {"key1": "value1", "ignore_me": "baz"},
        ]
    }
    expected_output = {(("key1", "value1"),), (("key2", "value2"),)}
    assert m._prepare_entry_as_set(input_data) == expected_output
