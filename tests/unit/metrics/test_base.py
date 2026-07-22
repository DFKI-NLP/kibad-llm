import pytest

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet, MetricWithTpFpFnEntries
from kibad_llm.metrics.collection import MetricCollectionWithFieldDiscoveryAndGrouping


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


def test_prepare_entry_as_set_processes_entries_with_configured_function():
    m = MetricWithPrepareEntryAsSet(process_entry_func=str.lower)

    assert m._prepare_entry_as_set(["Alpha", "BETA", "Alpha", None]) == {"alpha", "beta"}


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
    # if input is None, return empty set
    assert m._prepare_entry_as_set(None) == set()
    # if input is not None, raise ValueError
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


def test_prepare_entry_as_set_with_flatten_dicts():
    m = MetricWithPrepareEntryAsSet(field="items.label", flatten_dicts=True)
    input_data = {
        "items": [
            {"label": "x", "ignored": None},
            {"label": "y"},
            {"label": "x"},
        ],
        "empty": "   ",
    }
    assert m._prepare_entry_as_set(input_data) == {"x", "y"}


def test_metric_with_tpfpfn_entries_update_tracks_state_and_counts():
    m = MetricWithTpFpFnEntries()

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A"], record_id="record-2")

    assert m.state == {
        "tp": {("record-1", "A"), ("record-2", "A")},
        "fp": {("record-1", "B")},
        "fn": {("record-1", "C")},
    }
    assert m.state_count == {"tp": 2, "fp": 1, "fn": 1}


def test_metric_with_tpfpfn_entries_ignore_missing_entries_skips_one_sided_updates():
    m = MetricWithTpFpFnEntries(ignore_missing_entries=True)

    m.update(prediction="A", reference=None, record_id="record-1")
    m.update(prediction=None, reference="B", record_id="record-2")
    m.update(prediction="C", reference="C", record_id="record-3")

    assert m.state == {"tp": {("record-3", "C")}, "fp": set(), "fn": set()}
    assert m.state_per_record == {"record-3": {"tp": {"C"}, "fp": set(), "fn": set()}}


def test_metric_collection_field_overrides_replace_default_metric_kwargs_for_one_field():
    """Field overrides should take precedence without affecting other created metrics."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=MetricWithTpFpFnEntries,
        fields=["overridden", "default"],
        ignore_missing_entries=True,
        field_overrides={"overridden": {"ignore_missing_entries": False}},
    )

    m.update({"overridden": "A", "default": "B"}, {}, record_id="record-1")

    assert m.metrics["overridden"].ignore_missing_entries is False
    assert m.metrics["overridden"].state_count == {"tp": 0, "fp": 1, "fn": 0}
    assert m.metrics["default"].ignore_missing_entries is True
    assert m.metrics["default"].state_count == {"tp": 0, "fp": 0, "fn": 0}


def test_metric_with_tpfpfn_entries_generates_record_ids(caplog):
    m = MetricWithTpFpFnEntries()

    with caplog.at_level("WARNING", logger="kibad_llm.metrics.base"):
        m.update(prediction="A", reference="A")
        m.update(prediction="B", reference="C")

    assert m.state == {"tp": {(1, "A")}, "fp": {(2, "B")}, "fn": {(2, "C")}}
    assert "generated record id: 1" in caplog.text
    assert "generated record id: 2" in caplog.text


def test_metric_with_tpfpfn_entries_state_per_record_groups_entries():
    m = MetricWithTpFpFnEntries()

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A", "D"], record_id="record-2")

    assert m.state_per_record == {
        "record-1": {"tp": {"A"}, "fp": {"B"}, "fn": {"C"}},
        "record-2": {"tp": {"A"}, "fp": set(), "fn": {"D"}},
    }


def test_metric_with_tpfpfn_entries_reset_clears_state():
    m = MetricWithTpFpFnEntries()

    m.update(prediction=["A"], reference=["B"], record_id="record-1")
    m.reset()

    assert m.state == {"tp": set(), "fp": set(), "fn": set()}
    assert m.state_count == {"tp": 0, "fp": 0, "fn": 0}
    assert m.state_per_record == {}


def test_metric_with_tpfpfn_entries_reset_restarts_generated_record_ids(caplog):
    m = MetricWithTpFpFnEntries()

    with caplog.at_level("WARNING", logger="kibad_llm.metrics.base"):
        m.update(prediction="A", reference="A")
        m.update(prediction="B", reference="C")
        m.reset()
        m.update(prediction="D", reference="D")

    assert m.state == {"tp": {(1, "D")}, "fp": set(), "fn": set()}
    assert caplog.text.count("generated record id: 1") == 2
    assert "generated record id: 2" in caplog.text
