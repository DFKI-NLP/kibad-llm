from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Mapping as ABCMapping
from typing import Any, Optional


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


def build_schema_description(schema: dict[str, Any]) -> str:
    """
    Build a human-readable German summary for a JSON Schema.

    Creates a newline-separated description that includes:
    - Optional "Beschreibung:" from the schema-level "description".
    - A header "Feldhinweise und erlaubte Werte:".
    - One line per property from "properties" in the form
      "- <name>: <description> [Zulässige Werte: v1; v2; ...]" when an enum exists.

    Enums are taken from:
    - the property's "enum",
    - a local "$ref" on the property (e.g., "#/$defs/Name"), or
    - for arrays, the "items" schema's "enum" or its local "$ref".

    Only local "$ref" targets are resolved.
    """
    lines = []
    desc = schema.get("description", "")
    if desc:
        lines.append(f"Beschreibung: {desc}")
    lines.append("Feldhinweise und erlaubte Werte:")
    props = schema.get("properties", {}) or {}
    for name, spec in props.items():
        pdesc = spec.get("description", "")
        enum: list[str] | None = None

        # 1) direct enum on the property
        enum = spec.get("enum")

        # 2) enum via $ref on the property
        if enum is None and "$ref" in spec:
            ref_schema = _resolve_ref(schema, spec["$ref"])
            if ref_schema:
                enum = ref_schema.get("enum")

        # 3) arrays: enum on items or via $ref on items
        if enum is None and spec.get("type") == "array":
            items = spec.get("items")
            if isinstance(items, ABCMapping):
                enum = items.get("enum")
                if enum is None and "$ref" in items:
                    ref_schema = _resolve_ref(schema, items["$ref"])
                    if ref_schema:
                        enum = ref_schema.get("enum")

        hint = f"- {name}: {pdesc}" if pdesc else f"- {name}:"
        if enum:
            hint += " Zulässige Werte: " + "; ".join(enum)
        lines.append(hint)
    return "\n".join(lines)
