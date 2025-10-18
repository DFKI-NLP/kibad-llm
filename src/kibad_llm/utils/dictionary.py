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


def unflatten_dict(d: dict[tuple[str, ...], Any]) -> dict[str, Any] | Any:
    """Unflattens a dictionary with nested tuple keys. A dictionary with an empty tuple as the key
    is considered a root key, in which case the value is returned directly.

    Additionally, this version raises an error if there is a conflict such that one key tries
    to treat another key's value as a dictionary. For example:
        {("a",): 1, ("a", "b"): 2}
    should raise a ValueError.

    Example:
        >>> d = {("a", "b", "c"): 1, ("a", "b", "d"): 2, ("a", "e"): 3}
        >>> unflatten_dict(d)
        {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}
    """
    result: dict[str, Any] = {}

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

    return result
