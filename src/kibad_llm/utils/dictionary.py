from collections.abc import Iterable, MutableMapping
from typing import Any


def _flatten_dict_gen(
    d: MutableMapping | list,
    parent_key: tuple[str | int, ...] = (),
) -> Iterable[tuple[tuple[str | int, ...], Any]]:
    entries_iter: Iterable[tuple[str | int, Any]]
    if isinstance(d, MutableMapping):
        entries_iter = d.items()
    else:
        entries_iter = enumerate(d)
    for k, v in entries_iter:
        new_key = parent_key + (k,)
        if isinstance(v, (MutableMapping, list)):
            yield from _flatten_dict_gen(v, new_key)
        else:
            yield new_key, v


def flatten_dict(
    d: Any, parent_key: tuple[str | int, ...] = ()
) -> dict[tuple[str | int, ...], Any]:
    """Flatten a nested dictionary with tuple keys. If the input is not a dictionary, it returns a
    dictionary with an empty tuple as the key and the input value as the value.

    Examples:
        >>> d = {"a": {"b": 1, "c": 2}, "d": 3}
        >>> flatten_dict(d) == {("a", "b"): 1, ("a", "c"): 2, ("d",): 3}
        True

        # also works with lists
        >>> d = {"a": [{"b": 1}, {"c": [2, 3]}], "d": 4}
        >>> flatten_dict(d) == {("a", 0, "b"): 1, ("a", 1, "c", 0): 2, ("a", 1, "c", 1): 3, ("d",): 4}
        True
    """
    if not isinstance(d, (MutableMapping, list)):
        return {parent_key: d}
    return dict(_flatten_dict_gen(d, parent_key=parent_key))


def unflatten_dict(d: dict[tuple[str | int, ...], Any]) -> dict[str, Any] | list | Any:
    """Unflattens a dictionary with nested tuple keys. A dictionary with an empty tuple as the key
    is considered a root key, in which case the value is returned directly. Dictionary keys can be
    strings or integers. Integer keys indicate list indices and will be converted to lists in the
    final output.

    Additionally, this version raises an error if there is a conflict such that one key tries
    to treat another key's value as a dictionary. For example:
        {("a",): 1, ("a", "b"): 2}
    should raise a ValueError.

    Example:
        >>> d = {("a", "b", "c"): 1, ("a", "b", "d"): 2, ("a", "e"): 3}
        >>> unflatten_dict(d)
        {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}

        # converts integer keys back to lists (note the None padding)
        >>> d = {("a", 0): 1, ("a", 1): 2, ("b", 1, "c"): 3}
        >>> unflatten_dict(d)
        {'a': [1, 2], 'b': [None, {'c': 3}]}
    """
    # keys may be str or int, but int keys indicate lists and will be converted later
    result: dict[str | int, Any] = {}

    for path, value in d.items():
        # If the key path is empty, this is a direct value return:
        if not path:
            # If there's already something in result or if this isn't the only item, it's invalid
            if result or len(d) > 1:
                raise ValueError(
                    "Conflict at root level: trying to descend into a non-dict value."
                )
            return value

        # Walk through the path to create/find intermediate dictionaries
        current = result
        for key in path[:-1]:
            # If we've already stored a non-dict object at this key, it's a conflict
            if key in current and not isinstance(current[key], dict):
                raise ValueError(
                    f"Conflict at path {path}: trying to descend into a non-dict value {current[key]}."
                )
            # Use `setdefault` to ensure we have a dict here
            current = current.setdefault(key, {})

        # If we are about to assign to a key that already holds a dict, that's a conflict
        if path[-1] in current and isinstance(current[path[-1]], dict):
            raise ValueError(
                f"Conflict at path {path}: trying to overwrite existing dict with a non-dict value."
            )

        current[path[-1]] = value

    # convert dicts keyed by ints into lists (pad with None)
    def _to_lists(obj: Any) -> Any:
        if isinstance(obj, dict):
            for k in list(obj.keys()):
                obj[k] = _to_lists(obj[k])
            if obj and all(isinstance(k, int) for k in obj.keys()):
                max_idx = max(obj.keys())
                lst = [None] * (max_idx + 1)
                for i, v in obj.items():
                    lst[i] = v
                return lst
        elif isinstance(obj, list):
            return [_to_lists(v) for v in obj]
        return obj

    return _to_lists(result)


def _join_strings_and_move_ints_to_end(
    entries: tuple[str | int, ...], sep: str = "."
) -> tuple[str | int, ...]:
    """Join string parts with `sep` and append integer parts.

    Args:
      entries: Tuple of strings and integers.
      sep: Separator used to join string parts. Defaults to ".".

    Returns:
      A tuple where the first element is the joined string and the remaining
      elements are the integers in original order.

    Example:
      >>> _join_strings_and_move_ints_to_end(("a", "b", 0, 1))
      ('a.b', 0, 1)
    """
    return (sep.join(str(k) for k in entries if not isinstance(k, int)),) + tuple(
        k for k in entries if isinstance(k, int)
    )


def _flatten_nested_list(l: list, remove_values: list | None = None, sort: bool = False) -> list:
    """Flatten an arbitrarily nested list to a single list.

    Args:
      l: Input list. Elements can be values or lists.
      remove_values: Values to drop from the flattened list. Defaults to None.
      sort: Whether to sort the flattened list. Defaults to False.

    Returns:
      A flat list. The result excludes values in remove_values. The result is sorted when sort is True.

    Examples:
      >>> _flatten_nested_list([1, [2, [3, None]], 4])
      [1, 2, 3, None, 4]
      >>> _flatten_nested_list([3, [2, 1, [2]]], remove_values=[2])
      [3, 1]
      >>> _flatten_nested_list([3, [None, 1]], remove_values=[None], sort=True)
      [1, 3]
    """
    flattened_list = []
    for item in l:
        if isinstance(item, list):
            flattened_list.extend(_flatten_nested_list(item))
        else:
            flattened_list.append(item)
    if remove_values is not None:
        flattened_list = [item for item in flattened_list if item not in remove_values]
    if sort:
        flattened_list = sorted(flattened_list)
    return flattened_list


def rearrange_dict(
    d: dict, key_sep: str = ".", lists_remove_values: list | None = None, lists_sort: bool = False
) -> dict:
    """Rearranges a nested dictionary (containing dicts and lists) such that:
    - all dict levels are outermost combined into a single key joined by `key_sep`, and
    - all list levels are innermost combined into a single flattened list.

    Args:
        d: input dictionary
        key_sep: separator to use when joining keys
        lists_remove_values: list of values to remove from flattened lists
        lists_sort: whether to sort the flattened lists
    Returns:
        rearranged dictionary
    """

    # flatten: keys will be tuples and values scalars (e.g. str, int)
    d_flat = flatten_dict(d)
    # rearrange levels: join string keys and move int keys to the end
    d_keys_rearranged = {
        _join_strings_and_move_ints_to_end(k, sep=key_sep): v for k, v in d_flat.items()
    }
    # unflatten dict: entries will be scalar values, lists, or nested lists
    d_rearranged = unflatten_dict(d_keys_rearranged)
    assert isinstance(d_rearranged, dict)
    # flatten all list entries (also remove unwanted values and sort if specified)
    d_flat_lists = {
        k: (
            _flatten_nested_list(v, remove_values=lists_remove_values, sort=lists_sort)
            if isinstance(v, list)
            else v
        )
        for k, v in d_rearranged.items()
    }
    return d_flat_lists
