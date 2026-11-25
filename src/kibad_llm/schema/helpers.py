from collections.abc import Mapping
from typing import Any


def _ref_path(ref: str) -> tuple[str, ...]:
    """Decode a local JSON Pointer; other reference formats are unsupported."""
    if ref == "#":
        return ()
    if not ref.startswith("#/"):
        raise ValueError(f"Only local JSON Pointer references are supported: {ref!r}")
    return tuple(part.replace("~1", "/").replace("~0", "~") for part in ref[2:].split("/"))


def _resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any] | None:
    """Resolve a local reference to a schema mapping, or return None if unresolved."""
    if ref != "#" and not ref.startswith("#/"):
        return None
    node: Any = schema
    for part in _ref_path(ref):
        if isinstance(node, Mapping):
            node = node.get(part)
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return None
    return node if isinstance(node, Mapping) else None
