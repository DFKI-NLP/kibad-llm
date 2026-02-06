import pytest

from kibad_llm.extractors import aggregation_utils as au


# -----------------------------
# make_hashable_simple
# -----------------------------
def test_make_hashable_simple_primitives_passthrough():
    assert au.make_hashable_simple(1) == 1
    assert au.make_hashable_simple("x") == "x"
    assert au.make_hashable_simple(None) is None
    assert au.make_hashable_simple(True) is True


def test_make_hashable_simple_list_set_tuple_dict_behavior():
    # list: sorted, None removed
    assert au.make_hashable_simple([3, None, 1, 2]) == (1, 2, 3)

    # set: sorted, None removed
    assert au.make_hashable_simple({3, None, 1, 2}) == (1, 2, 3)

    # tuple: order kept, None kept
    assert au.make_hashable_simple((3, None, 1)) == (3, None, 1)

    # dict: items sorted by key, None-valued entries removed
    assert au.make_hashable_simple({"b": 2, "a": 1, "c": None}) == (("a", 1), ("b", 2))


def test_make_hashable_simple_nested_structures():
    value = {
        "x": [2, None, 1],
        "y": None,
        "z": ({"b": None, "a": 3}, None, [5, 4]),
    }
    # dict: sorted items, None values removed
    # list: sorted, None removed
    # tuple: order preserved, None preserved
    expected = (
        ("x", (1, 2)),
        ("z", ((("a", 3),), None, (4, 5))),
    )
    assert au.make_hashable_simple(value) == expected


# -----------------------------
# collect_values_and_type_per_key
# -----------------------------
def test_collect_values_and_type_per_key_handles_missing_keys_and_none_outputs():
    structured_outputs = [
        {"a": 1},  # missing b
        None,  # whole output missing (skipped)
        {"b": "x"},  # missing a
        {"a": None, "b": "y"},  # explicit None
    ]
    values_per_key, type_per_key = au.collect_values_and_type_per_key(structured_outputs)

    # Note: the None entry is skipped entirely, so we only have 3 "rows" for each key
    assert values_per_key["a"] == [1, None, None]
    assert values_per_key["b"] == [None, "x", "y"]

    assert type_per_key["a"] is int
    assert type_per_key["b"] is str


def test_collect_values_and_type_per_key_all_values_none_yields_no_type_entry():
    values_per_key, type_per_key = au.collect_values_and_type_per_key([{"a": None}, {"a": None}])
    assert values_per_key["a"] == [None, None]
    assert "a" not in type_per_key  # never saw a non-None value


def test_collect_values_and_type_per_key_type_mismatch_raises():
    with pytest.raises(au.AggregationError, match="Inconsistent types for key 'a'"):
        au.collect_values_and_type_per_key([{"a": 1}, {"a": "1"}])


def test_collect_values_and_type_per_key_skip_type_mismatch_sets_type_none():
    values_per_key, type_per_key = au.collect_values_and_type_per_key(
        [{"a": 1}, {"a": "1"}, {"a": 2}],
        skip_type_mismatches=True,
    )
    assert values_per_key["a"] == [1, "1", 2]
    assert type_per_key["a"] is None


# -----------------------------
# _majority_vote
# -----------------------------
def test_majority_vote_empty_list_raises():
    with pytest.raises(au.AggregationError, match="empty list"):
        au._majority_vote([])


def test_majority_vote_exclude_none_filters_and_can_return_none_if_all_none():
    assert au._majority_vote([None, None], exclude_none=True) is None
    assert au._majority_vote([None, 1, 1, 2], exclude_none=True) == 1


def test_majority_vote_tie_returns_none():
    assert au._majority_vote([1, 1, 2, 2], exclude_none=False) is None
    assert au._majority_vote([None, 1, 2], exclude_none=True) is None  # tie after filtering


def test_majority_vote_none_can_win_when_not_excluding():
    # None participates intentionally when exclude_none=False
    assert au._majority_vote([None, None, "x"], exclude_none=False) is None


# -----------------------------
# _multi_entry_majority_vote
# -----------------------------
def _as_hashable_set(items):
    """Compare list outputs without relying on ordering or unhashable items."""
    return {au.make_hashable_simple(i) for i in items}


def test_multi_entry_majority_vote_majority_over_lists():
    values = [[1, 2], [2, 3], [2]]
    assert au._multi_entry_majority_vote(values) == [2]


def test_multi_entry_majority_vote_ignores_none_lists_and_items_and_uses_n_default():
    values = [None, [1, None], [1]]
    # n defaults to len(values)=3; 1 appears twice -> 2 > 1.5 => included
    assert au._multi_entry_majority_vote(values) == [1]


def test_multi_entry_majority_vote_with_dict_items_dedup_by_hashable():
    d1 = {"a": 1, "b": None}
    d2 = {"a": 1}  # hash-equal to d1 due to None removal
    d3 = {"a": 2}
    values = [[d1], [d2], [d3]]
    # majority requires > 1.5; (a=1) appears twice
    result = au._multi_entry_majority_vote(values)
    assert _as_hashable_set(result) == {au.make_hashable_simple({"a": 1})}


# -----------------------------
# aggregate_majority_vote
# -----------------------------
def test_aggregate_majority_vote_all_none_returns_none():
    assert au.aggregate_majority_vote([None, None]) is None


def test_aggregate_majority_vote_primitives_missing_keys_and_none_participation():
    structured_outputs = [
        {"a": 1, "b": "x"},
        {"a": 1},  # missing b -> None
        {"a": None, "b": "x"},  # explicit None
    ]
    aggregated = au.aggregate_majority_vote(structured_outputs)

    # a values: [1,1,None] => majority 1
    assert aggregated["a"] == 1
    # b values: ["x",None,"x"] => majority "x"
    assert aggregated["b"] == "x"


def test_aggregate_majority_vote_dict_majority_uses_hashable_equivalence_and_returns_last_seen_mapping():
    d1 = {"a": 1, "b": None}
    d2 = {"a": 1}  # hash-equal to d1
    d3 = {"a": 2}
    structured_outputs = [{"d": d1}, {"d": d2}, {"d": d3}]
    aggregated = au.aggregate_majority_vote(structured_outputs)

    # hash-majority corresponds to {"a": 1}; mapping returns the last dict seen for that hash (d2)
    assert aggregated["d"] == d2


def test_aggregate_majority_vote_list_majority_items():
    structured_outputs = [
        {"tags": ["a", "b"]},
        {"tags": ["b", "c"]},
        {"tags": ["b"]},
    ]
    aggregated = au.aggregate_majority_vote(structured_outputs)
    assert aggregated["tags"] == ["b"]


def test_aggregate_majority_vote_type_mismatch_raises_by_default():
    with pytest.raises(au.AggregationError, match="Inconsistent types for key 'a'"):
        au.aggregate_majority_vote([{"a": 1}, {"a": "1"}])


def test_aggregate_majority_vote_type_mismatch_skip_sets_key_to_none():
    aggregated = au.aggregate_majority_vote(
        [{"a": 1}, {"a": "1"}, {"a": 2}],
        skip_type_mismatches=True,
    )
    assert aggregated["a"] is None


def test_aggregate_majority_vote_unsupported_type_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="Unsupported value type"):
        au.aggregate_majority_vote([{"x": {1, 2}}, {"x": {1, 2}}])


# -----------------------------
# _aggregate_unanimous
# -----------------------------
def test_aggregate_unanimous_private_all_none_returns_none():
    assert au._aggregate_unanimous([None, None]) is None


def test_aggregate_unanimous_private_identical_ignoring_none_returns_value():
    assert au._aggregate_unanimous([None, 1, 1]) == 1


def test_aggregate_unanimous_private_conflict_raises():
    with pytest.raises(au.AggregationError, match="Conflicting values"):
        au._aggregate_unanimous([1, 2, None])


# -----------------------------
# _multi_entry_union
# -----------------------------
def test_multi_entry_union_primitives_and_dicts_dedup_sorted_ignores_none():
    d1 = {"a": 1, "b": None}
    d2 = {"a": 2}
    d3 = {"a": 1}  # hash-equal to d1

    values = [[d1, None, d2], None, [d3]]
    result = au._multi_entry_union(values)

    # d1 and d3 hash-equal; mapping keeps the last seen (d3).
    assert result == [d3, d2]  # sorted by hashable: a=1 then a=2


# -----------------------------
# aggregate_unanimous (public)
# -----------------------------
def test_aggregate_unanimous_all_none_returns_none():
    assert au.aggregate_unanimous([None, None]) is None


def test_aggregate_unanimous_primitives_requires_unanimity_across_non_none():
    aggregated = au.aggregate_unanimous([{"a": 1}, {"a": None}, {"a": 1}])
    assert aggregated["a"] == 1

    with pytest.raises(au.AggregationError, match="Conflicting values"):
        au.aggregate_unanimous([{"a": 1}, {"a": 2}])


def test_aggregate_unanimous_dicts_consider_hashable_equivalence_and_return_last_seen():
    d1 = {"x": 1, "y": None}
    d2 = {"x": 1}
    structured_outputs = [{"d": d1}, {"d": d2}]
    aggregated = au.aggregate_unanimous(structured_outputs)
    assert aggregated["d"] == d2  # last seen for that hash


def test_aggregate_unanimous_lists_compare_via_hashable_and_return_last_seen():
    # lists are normalized (sorted, None removed) for comparison
    l1 = [3, None, 1, 2]
    l2 = [1, 2, 3]
    aggregated = au.aggregate_unanimous([{"l": l1}, {"l": l2}])
    assert aggregated["l"] == l2  # last seen for that hash


# -----------------------------
# aggregate_single_majority_vote_multi_union
# -----------------------------
def test_aggregate_single_majority_vote_multi_union_mixes_majority_for_single_and_union_for_lists():
    structured_outputs = [
        {"x": 1, "d": {"a": 1, "b": None}, "tags": ["b", "a"]},
        {"x": 1, "d": {"a": 1}, "tags": ["c", "b", None]},
        {"x": None, "d": None, "tags": None},
    ]
    aggregated = au.aggregate_single_majority_vote_multi_union(structured_outputs)

    # x: majority excluding None => [1,1] => 1
    assert aggregated["x"] == 1

    # d: majority excluding None; {"a":1,"b":None} hash-equal to {"a":1}; mapping returns last seen dict for that hash
    assert aggregated["d"] == {"a": 1}

    # tags: union across lists, sorted
    assert aggregated["tags"] == ["a", "b", "c"]


def test_aggregate_single_majority_vote_multi_union_tie_for_single_value_returns_none():
    structured_outputs = [{"x": 1}, {"x": 2}, {"x": None}]
    aggregated = au.aggregate_single_majority_vote_multi_union(structured_outputs)
    # exclude_none=True => [1,2] tie => None
    assert aggregated["x"] is None


def test_aggregate_single_majority_vote_multi_union_type_mismatch_skip_sets_key_none():
    aggregated = au.aggregate_single_majority_vote_multi_union(
        [{"x": 1}, {"x": "1"}],
        skip_type_mismatches=True,
    )
    assert aggregated["x"] is None
