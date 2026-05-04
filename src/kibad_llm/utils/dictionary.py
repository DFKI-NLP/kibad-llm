"""Dictionary utilities used across the codebase.

Key helpers:

- [`flatten_dict_simple`][kibad_llm.utils.dictionary.flatten_dict_simple] – flattens one level of nesting for lists-of-dicts
  (e.g., compound schema fields); used when converting structured predictions to sets
  for metric computation.
- [`flatten_dict`][kibad_llm.utils.dictionary.flatten_dict] / [`unflatten_dict`][kibad_llm.utils.dictionary.unflatten_dict] – deep flatten/unflatten with
  tuple keys and NaN padding; used by [`SaveJobReturnValueCallback`][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback]
  to reshape multirun result structures.
- [`flatten_dict_s`][kibad_llm.utils.dictionary.flatten_dict_s] – like [`flatten_dict`][kibad_llm.utils.dictionary.flatten_dict] but with a string separator,
  returning ``str`` keys directly.
- [`FieldDict`][kibad_llm.utils.dictionary.FieldDict] – a ``dict`` subclass backed by a ``dataclass``, keeping
  attribute assignment and dict-item assignment in sync.  Used as the base for
  [`SingleExtractionResult`][kibad_llm.extractors.base.SingleExtractionResult] so the result is both
  attribute-accessible and directly JSON-serialisable.
"""

from __future__ import annotations

from collections.abc import Generator, Mapping
import dataclasses
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)


def flatten_dict_simple(d: Mapping[str, Any], sep: str = ".") -> dict[str, Any]:
    """Flatten a dictionary with simple rules:
    - Keep only non-empty primitive values (str, int, float, bool)
    - For lists of primitives, keep as is
    - For lists of dicts, create new keys by combining parent key and child keys,
      and aggregate values into lists (removing duplicates and sorting)

    IMPORTANT: This function does not handle nested dicts beyond one level inside lists.

    Args:
        d: The dictionary to flatten.
        sep: The separator to use when combining keys.
    Returns:
        A flattened dictionary.
    """
    result: dict[str, Any] = dict()
    for k, v in d.items():
        # remove empty values
        if v is None or (isinstance(v, str) and v.strip() == ""):
            pass
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        elif isinstance(v, list):
            if all(isinstance(e, (str, int, float, bool)) for e in v):
                result[k] = v
            elif all(isinstance(e, dict) for e in v):
                current_keys = set()
                for e in v:
                    for k2, v2 in e.items():
                        if v2 is not None and not (isinstance(v2, str) and v2.strip() == ""):
                            (
                                result[f"{k}{sep}{k2}"].append(v2)
                                if f"{k}{sep}{k2}" in result
                                else result.setdefault(f"{k}{sep}{k2}", [v2])
                            )
                            current_keys.add(f"{k}{sep}{k2}")
                for k2 in current_keys:
                    result[k2] = sorted(set(result[k2]))
            else:
                raise ValueError(f"Cannot flatten list with mixed types: {v}")

    return result


KEYS_PAD = math.nan


def _flatten_dict_gen(d, parent_key: tuple[str | int, ...] = ()) -> Generator:
    for k, v in d.items():
        new_key = parent_key + (k,)
        if isinstance(v, dict):
            # no need to build an intermediate dict
            yield from _flatten_dict_gen(v, new_key)
        else:
            yield new_key, v


def flatten_dict(
    d: dict[str | int, Any], pad_keys: bool = True
) -> dict[tuple[str | int | float, ...], Any]:
    """Flattens a dictionary with nested keys. Per default, the keys are padded with np.nan to have
    the same length.

    Example:
        >>> d = {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}
        >>> flatten_dict(d)
        {('a', 'b', 'c'): 1, ('a', 'b', 'd'): 2, ('a', 'e', np.nan): 3}

        # with padding the keys
        >>> d = {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}
        >>> flatten_dict(d, pad_keys=False)
        {('a', 'b', 'c'): 1, ('a', 'b', 'd'): 2, ('a', 'e'): 3}
    """
    result: dict[tuple[str | int | float, ...], Any] = dict(_flatten_dict_gen(d))
    # pad the keys with np.nan to have the same length. We use np.nan to be pandas-friendly.
    if pad_keys:
        max_num_keys = max(len(k) for k in result.keys())
        result = {
            tuple(list(k) + [KEYS_PAD] * (max_num_keys - len(k))): v for k, v in result.items()
        }
    return result


def flatten_dict_s(d: dict[str | int, Any], sep: str = ".") -> dict[str, Any]:
    result: dict[tuple[str | int, ...], Any] = dict(_flatten_dict_gen(d))
    return {sep.join(str(ki) for ki in k): v for k, v in result.items()}


def unflatten_dict(
    d: dict[tuple[str | int | float, ...], Any], unpad_keys: bool = True
) -> dict[str | int | float, Any] | Any:
    """Unflattens a dictionary with nested keys. Per default, the keys are unpadded by removing
    np.nan values.

    Example:
        >>> d = {("a", "b", "c"): 1, ("a", "b", "d"): 2, ("a", "e"): 3}
        >>> unflatten_dict(d)
        {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}

        # with unpad the keys
        >>> d = {("a", "b", "c"): 1, ("a", "b", "d"): 2, ("a", "e", float("nan")): 3}
        >>> unflatten_dict(d)
        {'a': {'b': {'c': 1, 'd': 2}, 'e': 3}}
    """
    result: dict[str | int | float, Any] = {}
    for k, v in d.items():
        if unpad_keys:
            k = tuple(ki for ki in k if not (isinstance(ki, float) and math.isnan(ki)))
        if len(k) == 0:
            if len(result) > 1:
                raise ValueError("Cannot unflatten dictionary with multiple root keys.")
            return v
        current = result
        for key in k[:-1]:
            current = current.setdefault(key, {})
        current[k[-1]] = v
    return result


# not used
def get_and_map_keys(
    d: Mapping[str, Any],
    key: str,
    mapping: Mapping[str, str],
) -> dict[str, Any]:
    """Get a sub-dictionary from `d` by `key` and map its keys using `mapping`. If the key
    does not exist in `d` or its value is None, an empty dictionary is used.

    Args:
        d: The input dictionary.
        key: The key to get the sub-dictionary.
        mapping: A mapping from old keys to new keys.
    Returns:
        A new dictionary with mapped keys.
    """
    d_nested: Mapping[Any, Any] = d.get(key) or {}
    mapped = {mapping[k]: v for k, v in d_nested.items()}
    return mapped


def get(
    d: Mapping[str, Any],
    key: str,
    default: Any = None,
) -> Any:
    return d.get(key, default)


# This base is a "dataclass mixin" only so mypy knows `self` has dataclass metadata
# (dataclasses.fields / __dataclass_fields__). We disable auto-__init__ generation
# because subclasses should define the constructor via their own dataclass fields.
@dataclasses.dataclass(init=False)
class FieldDict(dict[str, Any]):
    """Dataclass-backed dict with a fixed set of keys.

    Keys correspond to dataclass fields. Attribute and item assignment stay in sync,
    so the object behaves like a real dict (e.g., for `json.dump(s)`), while still
    supporting typed field access.
    """

    def __post_init__(self) -> None:
        # Populate the underlying dict so json.dump sees a dict.
        for f in dataclasses.fields(self):
            dict.__setitem__(self, f.name, getattr(self, f.name))

    def __setattr__(self, name: str, value: Any) -> None:
        # Keep dict in sync when assigning attributes.
        object.__setattr__(self, name, value)
        if name in getattr(self, "__dataclass_fields__", {}):
            dict.__setitem__(self, name, value)

    def __setitem__(self, key: str, value: Any) -> None:
        # Keep attributes in sync when assigning like a dict.
        if key not in getattr(self, "__dataclass_fields__", {}):
            raise KeyError(f"Key '{key}' not found in {self.__class__.__name__}.")
        setattr(self, key, value)

    def __delitem__(self, key: str) -> None:
        raise TypeError(f"Deletion of items is not supported in {self.__class__.__name__}.")

    # Optional: block other mutating dict APIs that could desync semantics
    def pop(self, *args: Any, **kwargs: Any) -> Any:  # type: ignore[override]
        raise TypeError(f"pop() is not supported in {self.__class__.__name__}.")

    def clear(self) -> None:  # type: ignore[override]
        raise TypeError(f"clear() is not supported in {self.__class__.__name__}.")
