from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Mapping as ABCMapping
from typing import Any


def _resolve_ref(schema: Mapping[str, Any], ref: str) -> Mapping[str, Any] | None:
    """Resolve local JSON Schema $refs like '#/$defs/Name'."""
    if not ref.startswith("#/"):
        return None

    node: Mapping[str, Any] | None = schema
    for part in ref[2:].split("/"):
        # node may be None; get() returns Any | None
        next_node = None if node is None else node.get(part)
        if not isinstance(next_node, ABCMapping):
            return None
        # after isinstance, mypy narrows next_node to Mapping[Any, Any]
        node = next_node

    return node


def _extract_enum(schema: Mapping[str, Any], node: Any) -> list[str] | None:
    """
    Extract enum values from a schema node, handling:
    - inline 'enum'
    - direct '$ref'
    - composition via 'allOf'/'anyOf'/'oneOf' that contain refs or enums
    """
    if not isinstance(node, ABCMapping):
        return None

    # inline enum
    enum = node.get("enum")
    if isinstance(enum, list) and enum:
        return [str(v) for v in enum]

    # direct $ref
    ref = node.get("$ref")
    if isinstance(ref, str):
        ref_schema = _resolve_ref(schema, ref)
        if isinstance(ref_schema, ABCMapping):
            ref_enum = ref_schema.get("enum")
            if isinstance(ref_enum, list) and ref_enum:
                return [str(v) for v in ref_enum]

    # composition wrappers
    for key in ("allOf", "anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list):
            for sub in subs:
                values = _extract_enum(schema, sub)
                if values:
                    return values

    return None


def build_schema_description(schema: dict[str, Any]) -> str:
    """
    Build a human-readable German summary for a JSON Schema.

    Creates a newline-separated description that includes:
    - Optional "Beschreibung:" from the schema-level "description".
    - A header "Feldhinweise und erlaubte Werte:".
    - One line per property with description, cardinality, and allowed enum values.
    """
    lines = []
    desc = schema.get("description", "")
    if desc:
        lines.append(f"Beschreibung: {desc}")
    lines.append("Feldhinweise und erlaubte Werte (getrennt durch Semikolons):")

    props = schema.get("properties", {}) or {}
    for name, spec in props.items():
        pdesc = spec.get("description", "")

        is_array = spec.get("type") == "array"
        has_default = "default" in spec
        if is_array:
            cardinality = "0..*"
        else:
            cardinality = "0..1" if has_default else "1"

        # Extract enum values
        if is_array:
            items = spec.get("items")
            enum = _extract_enum(schema, items)
        else:
            enum = _extract_enum(schema, spec)

        hint = f"- {name}: {pdesc}" if pdesc else f"- {name}:"
        hint += f" Kardinalität: {cardinality}"
        if enum:
            hint += " | Zulässige Werte: " + "; ".join(enum)

        lines.append(hint)

    return "\n".join(lines)
