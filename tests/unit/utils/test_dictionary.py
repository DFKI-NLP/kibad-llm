import pytest

from kibad_llm.utils.dictionary import (
    flatten_dict,
    rearrange_dict,
    unflatten_dict,
)


def test_flatten_dict():
    d = {"a": {"b": 1, "c": 2}, "d": 3}
    assert flatten_dict(d) == {("a", "b"): 1, ("a", "c"): 2, ("d",): 3}

    assert flatten_dict({}) == {}
    assert flatten_dict(1) == {(): 1}


def test_flatten_dict_with_list():
    d = {"a": [1, 2], "b": [{"c": 3}]}
    assert flatten_dict(d) == {("a", 0): 1, ("a", 1): 2, ("b", 0, "c"): 3}

    # plain top level list
    d = [1, 2, 3]
    assert flatten_dict(d) == {(0,): 1, (1,): 2, (2,): 3}


def test_flatten_dict_with_list_nested():
    d = {"a": [{"b": 1}, {"c": [2, 3]}], "d": 4}
    assert flatten_dict(d) == {
        ("a", 0, "b"): 1,
        ("a", 1, "c", 0): 2,
        ("a", 1, "c", 1): 3,
        ("d",): 4,
    }


def test_flatten_dict_with_parent_key():
    d = {"a": {"b": 1, "c": 2}, "d": 3}
    assert flatten_dict(d, parent_key=("p",)) == {
        ("p", "a", "b"): 1,
        ("p", "a", "c"): 2,
        ("p", "d"): 3,
    }

    assert flatten_dict({}, parent_key=("p",)) == {}
    assert flatten_dict(1, parent_key=("p",)) == {("p",): 1}


def test_unflatten_dict():
    d_expected = {"a": {"b": 1, "c": 2}, "d": 3}
    assert unflatten_dict({("a", "b"): 1, ("a", "c"): 2, ("d",): 3}) == d_expected

    assert unflatten_dict({}) == {}

    assert unflatten_dict({(): 1}) == 1


def test_unflatten_dict_multiple_roots():
    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({("a", "b"): 1, ("a",): 2})
    assert (
        str(excinfo.value)
        == "Conflict at path ('a',): trying to overwrite existing dict with a non-dict value."
    )

    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({("a",): 1, (): 2})
    assert str(excinfo.value) == "Conflict at root level: trying to descend into a non-dict value."

    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({(): 1, ("b",): 2})
    assert str(excinfo.value) == "Conflict at root level: trying to descend into a non-dict value."

    # check more complex case
    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({("a", "b"): 1, ("a",): 2, ("a", "c"): 3})
    assert (
        str(excinfo.value)
        == "Conflict at path ('a',): trying to overwrite existing dict with a non-dict value."
    )

    # check more level of nesting
    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({("a", "b", "c"): 1, ("a", "b"): 2})
    assert (
        str(excinfo.value)
        == "Conflict at path ('a', 'b'): trying to overwrite existing dict with a non-dict value."
    )

    with pytest.raises(ValueError) as excinfo:
        unflatten_dict({("a", "b"): 1, ("a", "b", "c"): 2})


def test_unflatten_dict_with_lists():
    d = {("a", 0): 1, ("a", 1): 2, ("b", 1, "c"): 3}
    assert unflatten_dict(d) == {"a": [1, 2], "b": [{"c": 3}]}

    # more complex nesting
    d = {("a", 0, "b"): 1, ("a", 1, "c", 0): 2, ("a", 1, "c", 1): 3, ("d",): 4}
    assert unflatten_dict(d) == {"a": [{"b": 1}, {"c": [2, 3]}], "d": 4}

    # plain list
    d = {(0,): 1, (1,): 2, (2,): 3}
    assert unflatten_dict(d) == [1, 2, 3]


def test_flatten_and_unflatten_dict_with_lists():
    d = {"a": {"b": [1, 2]}, "c": [3, {"d": 4}]}
    assert flatten_dict(d) == {("a", "b", 0): 1, ("a", "b", 1): 2, ("c", 0): 3, ("c", 1, "d"): 4}

    d_back = unflatten_dict(flatten_dict(d))
    assert d_back == d


def test_rearrange_dict():
    d = {"a": {"b": [1, 2]}, "c": [3, {"d": 4}]}
    assert rearrange_dict(d) == {"a.b": [1, 2], "c": [3], "c.d": [4]}

    d = {"a": {"b": [1, None, 2]}, "c": [3, {"d": 4}], "e": None}
    assert rearrange_dict(d, lists_remove_values=[None]) == {
        "a.b": [1, 2],
        "c": [3],
        "c.d": [4],
        "e": None,
    }

    # lists_sort should be used together with lists_remove_values since sorting with None values fails
    d = {"a": {"b": [2, 1]}, "c": [3, {"d": 4}]}
    assert rearrange_dict(d, lists_remove_values=[None], lists_sort=True)
