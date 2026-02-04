import pytest

from kibad_llm.extractors.aggregation_utils import (
    _aggregate_unanimous,
    _majority_vote,
    _multi_entry_majority_vote,
    _multi_entry_union,
    aggregate_majority_vote,
    aggregate_single_unanimous_multi_union,
)

# --- Tests for _majority_vote ---


def test_majority_vote_basic():
    assert _majority_vote(["a", "b", "a", "c", "a"]) == "a"


def test_majority_vote_tie_returns_one_of():
    # In a tie, there is no majority; function should return None
    res = _majority_vote(["x", "y"])
    assert res is None


def test_majority_vote_empty_raises():
    with pytest.raises(ValueError, match="majority vote on empty list"):
        _majority_vote([])


# --- Tests for _multi_entry_majority_vote ---


def test_multi_entry_majority_vote_basic():
    values = [["x", "y"], ["x"], ["y", "z"]]
    # n defaults to len(values)=3; majority threshold is > 1.5 -> 2
    res = _multi_entry_majority_vote(values)
    assert set(res) == {"x", "y"}


def test_multi_entry_majority_vote_handles_none_and_default_n():
    values = [["a"], None, ["a", "b"]]
    # n defaults to 3; 'a' appears twice -> included; 'b' appears once -> excluded
    res = _multi_entry_majority_vote(values)
    assert res == ["a"]


def test_multi_entry_majority_vote_with_explicit_n_strict_threshold():
    values = [["a"], ["a"]]
    # Explicit n=4 -> need > 2 occurrences; only 2 present -> exclude
    res = _multi_entry_majority_vote(values, n=4)
    assert res == []


def test_multi_entry_majority_vote_empty_values_returns_empty():
    assert _multi_entry_majority_vote([]) == []


def test_multi_entry_majority_vote_dict_entries():
    # lists consisting of dicts
    values = [[{"k1": "v1", "k2": None}, {"k1": "v2"}], [{"k1": "v1"}], [{"k1": "v3"}]]
    res = _multi_entry_majority_vote(values)
    assert res == [{"k1": "v1"}]


def test_multi_entry_majority_vote_dict_entries_with_lists():
    # lists consisting of dicts with list values
    values = [
        [{"k1": ["v1", None], "k2": None}, {"k1": ["v2"]}],
        [{"k1": ["v1"]}],
        [{"k1": ["v3"]}],
    ]
    res = _multi_entry_majority_vote(values)
    assert res == [{"k1": ["v1"]}]


# --- Tests for _aggregate_structured_outputs ---


def test_aggregate_structured_outputs_primitives_majority_with_nones():
    # Mix of primitives with some None values
    structured_outputs = [
        {"s": "a", "i": 1, "f": 1.0, "b": True},
        {"s": "a", "i": 2, "f": 2.0, "b": False},
        {"s": "a", "i": 2, "f": 2.0, "b": False, "extra": None},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res["s"] == "a"
    assert res["i"] == 2
    assert res["f"] == 2.0
    assert res["b"] is False
    # 'extra' is only None everywhere -> should be present as None
    assert "extra" in res and res["extra"] is None


def test_aggregate_structured_outputs_lists_majority_with_missing_entries():
    # Key 'l' missing entirely in one extraction; majority computed with n=len(results)=3
    structured_outputs = [
        {"l": ["x"]},
        {},  # key missing
        {"l": ["x", "y"]},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res["l"] == ["x"]


def test_aggregate_structured_outputs_lists_with_nones():
    structured_outputs = [
        {"l": None},
        {"l": ["a"]},
        {"l": None},
    ]
    # n=3; 'a' occurs once -> not > 1.5; expect empty list
    res = aggregate_majority_vote(structured_outputs)
    assert res["l"] == []


def test_aggregate_structured_outputs_all_none_results_in_none():
    structured_outputs = [{"x": None}, {"x": None}]
    res = aggregate_majority_vote(structured_outputs)
    assert res["x"] is None


def test_aggregate_structured_outputs_dict():
    # None values inside dicts should be ignored in majority vote
    structured_outputs = [
        {"d": {"k1": 1, "k2": None, "k3": 3}},
        {"d": {"k1": 1, "k3": 3}},
        {"d": {"k1": [1, 2, 3], "k3": 3}},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res == {"d": {"k1": 1, "k3": 3}}


def test_aggregate_structured_outputs_dict_tie():
    structured_outputs = [
        {"d": {"k1": 0, "k2": 2}},
        {"d": {"k1": 1, "k2": 2}},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res == {"d": None}


def test_aggregate_structured_outputs_inconsistent_types_raises():
    structured_outputs = [{"k": 1}, {"k": "1"}]
    with pytest.raises(ValueError, match="Inconsistent types for key 'k'"):
        aggregate_majority_vote(structured_outputs)


def test_aggregate_structured_outputs_missing_first_key():

    structured_outputs = [
        {"A": None},
        {"A": 1},
        {"A": 2},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res == {"A": None}

    # the result should be the same even if the first entry has the key missing
    structured_outputs2 = [
        {},
        {"A": 1},
        {"A": 2},
    ]
    res2 = aggregate_majority_vote(structured_outputs2)
    assert res2 == {"A": None}


def test_aggregate_structured_outputs_none():

    # if at least one entry has a value, it should be used
    structured_outputs = [
        None,
        {"A": 1},
    ]
    res = aggregate_majority_vote(structured_outputs)
    assert res == {"A": 1}

    # if all entries are None, the result should be None
    structured_outputs2 = [
        None,
        None,
    ]
    res2 = aggregate_majority_vote(structured_outputs2)
    assert res2 is None


class TestUnionSingle:
    def test_all_same_values(self):
        assert _aggregate_unanimous([1, 1, 1]) == 1
        assert _aggregate_unanimous(["a", "a"]) == "a"

    def test_with_none_values(self):
        assert _aggregate_unanimous([1, None, 1]) == 1
        assert _aggregate_unanimous([None, "a", None, "a"]) == "a"

    def test_all_none(self):
        assert _aggregate_unanimous([None, None]) is None

    def test_empty_list(self):
        assert _aggregate_unanimous([]) is None

    def test_conflicting_values(self):
        with pytest.raises(ValueError, match="Conflicting values"):
            _aggregate_unanimous([1, 2, 3])


class TestMultiEntryUnion:
    def test_union_of_lists(self):
        result = _multi_entry_union([[1, 2], [2, 3], [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_with_none_lists(self):
        result = _multi_entry_union([[1, 2], None, [3, 4]])
        assert result == [1, 2, 3, 4]

    def test_with_dicts(self):
        result = _multi_entry_union([[{"a": 1}, {"b": 2}], [{"a": 1}]])
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_lists(self):
        assert _multi_entry_union([[], []]) == []


class TestAggregateStructuredOutputs:
    def test_primitive_types(self):
        outputs = [{"name": "John", "age": 30}, {"name": "John"}]
        result = aggregate_single_unanimous_multi_union(outputs)
        assert result == {"name": "John", "age": 30}

    def test_list_union(self):
        outputs = [{"tags": ["a", "b"]}, {"tags": ["b", "c"]}]
        result = aggregate_single_unanimous_multi_union(outputs)
        assert result == {"tags": ["a", "b", "c"]}

    def test_all_none(self):
        assert aggregate_single_unanimous_multi_union([None, None]) is None

    def test_type_mismatch_raises(self):
        outputs = [{"value": 1}, {"value": "string"}]
        with pytest.raises(ValueError, match="Inconsistent types"):
            aggregate_single_unanimous_multi_union(outputs)

    def test_type_mismatch_skip(self):
        outputs = [{"value": 1}, {"value": "string"}]
        result = aggregate_single_unanimous_multi_union(outputs, skip_type_mismatches=True)
        assert result == {"value": None}

    def test_conflicting_primitives(self):
        outputs = [{"name": "John"}, {"name": "Jane"}]
        with pytest.raises(ValueError, match="Conflicting values"):
            aggregate_single_unanimous_multi_union(outputs)
