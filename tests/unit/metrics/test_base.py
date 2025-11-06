import pytest

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet


def test_prepare_entry_as_set():
    m = MetricWithPrepareEntryAsSet()
    assert m._prepare_entry_as_set(None) == set()
    assert m._prepare_entry_as_set("x") == {"x"}
    assert m._prepare_entry_as_set(["a", "a", "b"]) == {"a", "b"}
    # Passing a dict without a field leads to an unhashable element; ensure this is surfaced
    with pytest.raises(TypeError):
        m._prepare_entry_as_set({"labels": ["a"]})


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
    expected_output_mixed = {(("key1", "value1"),), "simple_value", (("key2", "value2"),), None}
    assert m._prepare_entry_as_set(input_data_mixed) == expected_output_mixed


def test_prepare_entry_as_set_with_field():
    m = MetricWithPrepareEntryAsSet(field="labels")
    assert m._prepare_entry_as_set({"labels": ["x", "y", "y"]}) == {"x", "y"}
    assert m._prepare_entry_as_set({"other": "z"}) == set()
    assert m._prepare_entry_as_set({"labels": None}) == set()
