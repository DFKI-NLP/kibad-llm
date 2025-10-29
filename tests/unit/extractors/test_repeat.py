import pytest

from kibad_llm.extractors.repeat import (
    _aggregate_structured_outputs,
    _majority_vote,
    _multi_entry_majority_vote,
)

# --- Tests for _majority_vote ---


def test_majority_vote_basic():
    assert _majority_vote(["a", "b", "a", "c", "a"]) == "a"


def test_majority_vote_tie_returns_one_of():
    # In a tie, any of the tied values is acceptable
    res = _majority_vote(["x", "y"])
    assert res in {"x", "y"}


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


# --- Tests for _aggregate_structured_outputs ---


def test_aggregate_structured_outputs_primitives_majority_with_nones():
    # Mix of primitives with some None values
    structured_outputs = [
        {"s": "a", "i": 1, "f": 1.0, "b": True},
        {"s": "a", "i": 2, "f": 2.0, "b": False},
        {"s": "a", "i": 2, "f": 2.0, "b": False, "extra": None},
    ]
    res = _aggregate_structured_outputs(structured_outputs)
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
    res = _aggregate_structured_outputs(structured_outputs)
    assert res["l"] == ["x"]


def test_aggregate_structured_outputs_lists_with_nones():
    structured_outputs = [
        {"l": None},
        {"l": ["a"]},
        {"l": None},
    ]
    # n=3; 'a' occurs once -> not > 1.5; expect empty list
    res = _aggregate_structured_outputs(structured_outputs)
    assert res["l"] == []


def test_aggregate_structured_outputs_all_none_results_in_none():
    structured_outputs = [{"x": None}, {"x": None}]
    res = _aggregate_structured_outputs(structured_outputs)
    assert res["x"] is None


def test_aggregate_structured_outputs_dict_value_raises():
    structured_outputs = [{"d": {"k": "v"}}, {"d": {"k": "w"}}]
    with pytest.raises(
        ValueError, match="Dict type values is not yet implemented|dict type values"
    ):
        _aggregate_structured_outputs(structured_outputs)


def test_aggregate_structured_outputs_inconsistent_types_raises():
    structured_outputs = [{"k": 1}, {"k": "1"}]
    with pytest.raises(ValueError, match="Inconsistent types for key 'k'"):
        _aggregate_structured_outputs(structured_outputs)


def test_aggregate_structured_outputs_missing_first_key():

    structured_outputs = [
        {"A": None},
        {"A": 1},
        {"A": 2},
    ]
    res = _aggregate_structured_outputs(structured_outputs)
    assert res == {"A": None}

    # the result should be the same even if the first entry has the key missing
    structured_outputs2 = [
        {},
        {"A": 1},
        {"A": 2},
    ]
    res2 = _aggregate_structured_outputs(structured_outputs2)
    assert res2 == {"A": None}


def test_aggregate_structured_outputs_none():

    # if at least one entry has a value, it should be used
    structured_outputs = [
        None,
        {"A": 1},
    ]
    res = _aggregate_structured_outputs(structured_outputs)
    assert res == {"A": 1}

    # if all entries are None, the result should be None
    structured_outputs2 = [
        None,
        None,
    ]
    res2 = _aggregate_structured_outputs(structured_outputs2)
    assert res2 is None
