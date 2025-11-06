import pytest

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet


def test_prepare_entry_as_set():
    cm = MetricWithPrepareEntryAsSet()
    assert cm._prepare_entry_as_set(None) == set()
    assert cm._prepare_entry_as_set("x") == {"x"}
    assert cm._prepare_entry_as_set(["a", "a", "b"]) == {"a", "b"}
    # Passing a dict without a field leads to an unhashable element; ensure this is surfaced
    with pytest.raises(TypeError):
        cm._prepare_entry_as_set({"labels": ["a"]})


def test_prepare_entry_as_set_with_field():
    cm_field = MetricWithPrepareEntryAsSet(field="labels")
    assert cm_field._prepare_entry_as_set({"labels": ["x", "y", "y"]}) == {"x", "y"}
    assert cm_field._prepare_entry_as_set({"other": "z"}) == set()
    assert cm_field._prepare_entry_as_set({"labels": None}) == set()
