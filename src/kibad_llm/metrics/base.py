from collections.abc import Hashable
from typing import Any, overload

from kibad_llm.metric import Metric


@overload
def _make_hashable_and_order_normalize(
    value: tuple | set | dict | list, _seen: set[int] | None = None
) -> tuple[Hashable, ...]: ...


@overload
def _make_hashable_and_order_normalize(value: Any, _seen: set[int] | None = None) -> Hashable: ...


def _make_hashable_and_order_normalize(
    value: Any, _seen: set[int] | None = None
) -> Hashable | tuple[Hashable, ...]:
    """Return a hashable, order-normalized equivalent of the input value.
    Handles dict, list, tuple, set. Dicts, lists, and sets are converted to tuples with sorted
    elements to ensure order normalization.
    Tuples are converted to tuples without sorting to preserve order.
    Scalar values are returned as-is after checking they are hashable.
    Protects against cycles.
    """
    if _seen is None:
        _seen = set()
    obj_id = id(value)
    if obj_id in _seen:
        raise ValueError("Cycle detected in structure")
    _seen.add(obj_id)
    try:
        if isinstance(value, dict):
            return tuple(
                # sort by repr of key to ensure consistent ordering
                sorted(
                    ((k, _make_hashable_and_order_normalize(v, _seen)) for k, v in value.items()),
                    key=lambda kv: kv[0],
                )
            )
        if isinstance(value, (list, set)):
            return tuple(
                # sort by repr to ensure consistent ordering
                sorted(
                    _make_hashable_and_order_normalize(v, _seen) for v in value if v is not None
                )
            )
        if isinstance(value, tuple):
            # don't sort tuples, just convert elements
            return tuple(_make_hashable_and_order_normalize(v, _seen) for v in value)
        # Ensure scalar is hashable
        hash(value)
        return value
    finally:
        _seen.remove(obj_id)


class MetricWithPrepareEntryAsSet(Metric):
    """Base class for metrics that require preparing entries as sets.

    Args:
        field: Optional; If provided, the field to extract from a dict entry.
    """

    def __init__(self, field: str | None = None) -> None:
        self.field = field
        super().__init__()

    def _prepare_entry_as_set(self, entry: Any) -> set:
        """Helper method to convert any prediction or reference value into a set of values.

        Uses the provided field to retrieve the correct values from a given dict if necessary.
        Returns empty set when there is no value.
        Wraps any found values into a set whilst keeping the unique values unaltered

        Args:
            entry: Any kind of data structure to maybe extract from and eventually wrap in a set.
        Returns: A set of whatever relevant value was put in.
        """
        if self.field is not None:
            if not isinstance(entry, dict):
                raise ValueError(
                    f"Expected entry to be a dict when field is set, but got {type(entry)}"
                )
            entry = entry.get(self.field, None)
        if entry is None:
            return set()

        entry_hashable = _make_hashable_and_order_normalize(entry)
        # multi-value case
        if isinstance(entry, (list, set)):
            return set(entry_hashable)
        # single-value case (also includes tuples and dicts)
        else:
            return {entry_hashable}
