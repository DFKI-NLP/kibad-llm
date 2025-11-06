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


def test_prepare_entry_as_set_with_field():
    m = MetricWithPrepareEntryAsSet(field="labels")
    assert m._prepare_entry_as_set({"labels": ["x", "y", "y"]}) == {"x", "y"}
    assert m._prepare_entry_as_set({"other": "z"}) == set()
    assert m._prepare_entry_as_set({"labels": None}) == set()
