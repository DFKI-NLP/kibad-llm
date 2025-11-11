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
    schema: Mapping[str, Any],
    header: str | None = "Feldhinweise und erlaubte Werte (getrennt durch Semikolons):",
    description_prefix: str = "Beschreibung: ",
    cardinality_prefix: str = "Kardinalität: ",
    type_prefix: str = "Typ: ",
    enum_prefix: str = "Zulässige Werte: ",
    component_separator: str = " | ",
    enum_separator: str = "; ",
    indent_step: str = "  ",
    # internal args
    indent: int = 0,
    root_schema: Mapping[str, Any] | None = None,
) -> str:
    """
    Build a human‑readable summary for a JSON Schema.

    Output format:
    - Optional first line: "<description_prefix><schema.description>" if present
    - Optional header line (only at top level if header is not None)
    - One line per property:
      "<indent>- <name>: <description><separator><cardinality_prefix><cardinality><separator><type_prefix><type>[<separator><enum_prefix><values>]"
    - For nested objects, recursively includes their properties with increased indentation

    Cardinality rules:
    - type=array ⇒ "0..*"
    - non-array with "default" ⇒ "0..1"
    - non-array without "default" ⇒ "1"

    Type extraction:
    - Supports inline "type", direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf"
    - For arrays, type is taken from "items"

    Enum extraction:
    - Supports inline "enum", direct "$ref", and compositions via "allOf"/"anyOf"/"oneOf"
    - For arrays, enums are taken from "items" (including "$ref" or compositions)

    Args:
        schema: The JSON Schema dictionary to process
        header: Header text for field list (only shown at top level, None to omit)
        description_prefix: Prefix for schema descriptions
        cardinality_prefix: Prefix for cardinality information
        type_prefix: Prefix for type information
        enum_prefix: Prefix for enum value lists
        component_separator: Separator between field components (name, cardinality, type, enum)
        enum_separator: Separator between individual enum values
        indent_step: String used for each indentation level
        indent: Current indentation level (internal, for recursion)
        root_schema: Root schema containing $defs (internal, for recursion)

    Returns:
        Multi-line string summarizing schema structure, fields, and constraints
    """
    if root_schema is None:
        root_schema = schema

    lines = []
    prefix = indent_step * indent

    # Add description
    desc = schema.get("description", "")
    if desc:
        lines.append(f"{prefix}{description_prefix}{desc}")

    if header:
        lines.append(header)

    props = schema.get("properties", {}) or {}
    for name, spec in props.items():
        pdesc = spec.get("description", "")

        # Single check for array vs non-array handling
        is_array = spec.get("type") == "array"
        target = spec.get("items") if is_array else spec

        # Determine cardinality
        has_default = "default" in spec
        cardinality = "0..*" if is_array else ("0..1" if has_default else "1")

        # Extract type and enum from target
        field_type = _extract_type(root_schema, target)
        enum = _extract_enum(root_schema, target)

        # Build field line
        hint = f"{prefix}- {name}: {pdesc}" if pdesc else f"{prefix}- {name}:"
        hint += f"{component_separator}{cardinality_prefix}{cardinality}"
        if field_type:
            hint += f"{component_separator}{type_prefix}{field_type}"
        if enum:
            hint += f"{component_separator}{enum_prefix}" + enum_separator.join(enum)

        lines.append(hint)

        # Handle nested objects recursively
        if field_type == "object" and isinstance(target, ABCMapping):
            ref = target.get("$ref")
            if isinstance(ref, str):
                nested_schema = _resolve_ref(root_schema, ref)
                if nested_schema:
                    # Recursively process nested properties
                    nested_content = build_schema_description(
                        nested_schema,
                        indent=indent + 1,
                        root_schema=root_schema,
                        # no header for nested
                        header=None,
                        description_prefix=description_prefix,
                        cardinality_prefix=cardinality_prefix,
                        type_prefix=type_prefix,
                        enum_prefix=enum_prefix,
                        component_separator=component_separator,
                        enum_separator=enum_separator,
                        indent_step=indent_step,
                    )
                    lines.append(nested_content)

    return "\n".join(lines)
