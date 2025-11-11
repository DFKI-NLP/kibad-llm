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


def _extract_type(schema: Mapping[str, Any], node: Any) -> str | None:
    """
    Extract the type from a schema node, handling:
    - inline 'type'
    - direct '$ref' (resolves to 'object' for model refs)
    - composition via 'allOf'/'anyOf'/'oneOf'

    Returns:
        str: Type like "string", "integer", "number", "boolean", "array", "object", or None
    """
    if not isinstance(node, ABCMapping):
        return None

    # inline type
    node_type = node.get("type")
    if isinstance(node_type, str):
        return node_type

    # direct $ref
    ref = node.get("$ref")
    if isinstance(ref, str):
        ref_schema = _resolve_ref(schema, ref)
        if isinstance(ref_schema, ABCMapping):
            ref_type = ref_schema.get("type")
            if isinstance(ref_type, str):
                return ref_type

    # composition wrappers
    for key in ("allOf", "anyOf", "oneOf"):
        subs = node.get(key)
        if isinstance(subs, list):
            for sub in subs:
                sub_type = _extract_type(schema, sub)
                if sub_type:
                    return sub_type

    return None


def build_schema_description(
    schema: Mapping[str, Any], indent: int = 0, root_schema: Mapping[str, Any] | None = None
) -> str:
    """
    Build a human‑readable German summary for a JSON Schema.

    Output format:
    - Optional first line: "Beschreibung: <schema.description>" if present.
    - Header line: "Feldhinweise und erlaubte Werte (getrennt durch Semikolons):"
    - Then one line per property:
      "- <Name>: <Beschreibung> Kardinalität: <1|0..1|0..*> | Typ: <type>[ | Zulässige Werte: v1; v2; ...]"
      For nested objects, recursively include their properties with indentation.

    Cardinality rules:
    - type=array ⇒ "0..*"
    - non-array with a "default" ⇒ "0..1"
    - non-array without a "default" ⇒ "1"

    Type extraction:
    - Supports inline "type", direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf".
    - For arrays, type is taken from "items".

    Enum extraction:
    - Supports inline "enum", direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf".
    - For arrays, enums are taken from "items" (including "$ref" or compositions).

    Args:
        schema: The JSON Schema as a dictionary.
        indent: Current indentation level for nested objects.
        root_schema: The root schema containing $defs (defaults to schema if None).

    Returns:
        str: Multi-line German text summarizing fields and constraints.
    """
    if root_schema is None:
        root_schema = schema

    lines = []
    prefix = "  " * indent

    # Only add header at top level
    if indent == 0:
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

        # Extract type and enum (use root_schema for resolving refs)
        if is_array:
            items = spec.get("items")
            field_type = _extract_type(root_schema, items)
            enum = _extract_enum(root_schema, items)
        else:
            field_type = _extract_type(root_schema, spec)
            enum = _extract_enum(root_schema, spec)

        # Build field line
        hint = f"{prefix}- {name}: {pdesc}" if pdesc else f"{prefix}- {name}:"
        hint += f" Kardinalität: {cardinality}"
        if field_type:
            hint += f" | Typ: {field_type}"
        if enum:
            hint += " | Zulässige Werte: " + "; ".join(enum)

        lines.append(hint)

        # Handle nested objects recursively
        if field_type == "object":
            # Resolve the nested schema
            nested_schema = None
            if is_array:
                items = spec.get("items")
                if isinstance(items, ABCMapping):
                    ref = items.get("$ref")
                    if isinstance(ref, str):
                        nested_schema = _resolve_ref(root_schema, ref)
            else:
                ref = spec.get("$ref")
                if isinstance(ref, str):
                    nested_schema = _resolve_ref(root_schema, ref)

            if nested_schema:
                nested_desc = nested_schema.get("description", "")
                if nested_desc:
                    lines.append(f"{prefix}  Beschreibung: {nested_desc}")

                # Recursively process nested properties with root_schema
                nested_content = build_schema_description(nested_schema, indent + 1, root_schema)
                # No need to skip lines - indent > 0 doesn't add header
                lines.append(nested_content)

    return "\n".join(lines)
