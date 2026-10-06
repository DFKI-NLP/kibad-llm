"""Interpret JSON Schema documentation and render extraction prompt descriptions.

Descriptions retain their schema paths until they are assigned to fields, types, or
choices. Rendering never reinterprets a field annotation as type documentation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Literal

from kibad_llm.schema.utils import _ref_path, _resolve_ref
from kibad_llm.utils.log import warn_once


@dataclass(frozen=True)
class _Description:
    """One normalized annotation, identified by its location rather than its text."""

    source: tuple[str, ...]
    text: str
    role: Literal["type", "choices"] = "type"


def _description(node: Mapping[str, Any], path: tuple[str, ...]) -> _Description | None:
    """Read a description without assigning it a presentation role yet."""
    raw = node.get("description")
    text = " ".join(raw.split()) if isinstance(raw, str) else ""
    return _Description((*path, "description"), text) if text else None


def _unique_descriptions(descriptions: tuple[_Description, ...]) -> tuple[_Description, ...]:
    """Keep each annotation once within an occurrence, including equal text at distinct paths."""
    return tuple({description.source: description for description in descriptions}.values())


@dataclass(frozen=True)
class _Value:
    """A resolved display value; its descriptions document its type or enum choices."""

    type_name: str | None = None
    descriptions: tuple[_Description, ...] = ()
    choices: tuple[str, ...] | None = None
    fields: tuple[_Field, ...] = ()
    items: _Value | None = None


@dataclass(frozen=True)
class _Field:
    """A property occurrence with its own documentation, separate from its value type."""

    name: str
    description: _Description | None
    cardinality: str
    value: _Value


class _SchemaInterpreter:
    """Build a display tree while retaining annotation ownership through schema traversal."""

    def __init__(self, root: Mapping[str, Any]) -> None:
        """Keep the schema used for resolving local references."""
        self.root = root

    def field(
        self,
        name: str,
        node: Mapping[str, Any],
        path: tuple[str, ...],
        ancestors: frozenset[tuple[str, ...]],
    ) -> _Field:
        """Assign the property annotation to the field before any visibility filtering."""
        description = _description(node, path)
        value = self.value(node, path, ancestors)
        if description:
            value = replace(
                value,
                descriptions=tuple(
                    d for d in value.descriptions if d.source != description.source
                ),
            )
        cardinality = (
            "0..*" if value.type_name == "array" else ("0..1" if "default" in node else "1")
        )
        return _Field(name, description, cardinality, value)

    def value(
        self,
        node: Mapping[str, Any],
        path: tuple[str, ...] = (),
        ancestors: frozenset[tuple[str, ...]] = frozenset(),
    ) -> _Value:
        """Resolve a value and its children, rejecting references that cannot be expanded."""
        if path in ancestors:
            raise ValueError(f"Recursive schema cannot be expanded into a description: {path!r}")
        ancestors = ancestors | {path}
        own_description = _description(node, path)
        descriptions = (own_description,) if own_description else ()
        value = _Value()

        ref = node.get("$ref")
        if isinstance(ref, str):
            target = _resolve_ref(self.root, ref)
            if target is None:
                raise ValueError(f"Cannot resolve schema reference: {ref!r}")
            value = self.value(target, _ref_path(ref), ancestors)

        for keyword in ("allOf", "anyOf", "oneOf"):
            branches = node.get(keyword)
            if isinstance(branches, list) and branches:
                alternatives = tuple(
                    self.value(branch, (*path, keyword, str(index)), ancestors)
                    for index, branch in enumerate(branches)
                )
                value = self.composition(keyword, alternatives)
                break

        type_name = node.get("type", value.type_name)
        if type_name is not None and not isinstance(type_name, str):
            raise ValueError("Schema descriptions expect a single type or an anyOf/oneOf union.")
        if type_name is None and "properties" in node:
            type_name = "object"
        choices = value.choices
        if isinstance(node.get("enum"), list):
            choices = tuple(str(choice) for choice in node["enum"])
        if own_description and choices is not None:
            descriptions = (replace(own_description, role="choices"),)

        fields = value.fields
        if isinstance(node.get("properties"), Mapping):
            fields = tuple(
                self.field(name, spec, (*path, "properties", name), ancestors)
                for name, spec in node["properties"].items()
            )
        items = value.items
        if isinstance(node.get("items"), Mapping):
            items = self.value(node["items"], (*path, "items"), ancestors)
        return _Value(
            type_name=type_name,
            descriptions=_unique_descriptions(descriptions + value.descriptions),
            choices=choices,
            fields=fields,
            items=items,
        )

    @staticmethod
    def composition(keyword: str, alternatives: tuple[_Value, ...]) -> _Value:
        """Combine enum constraints, or select a representative non-null display branch.

        Structural unions remain summaries of one branch, as in the original formatter.
        Multi-branch object intersections require merging constraints and are unsupported.
        """
        non_null = tuple(value for value in alternatives if value.type_name != "null")
        selected = next(
            (value for value in non_null if value.type_name),
            non_null[0] if non_null else alternatives[0],
        )
        enums = tuple(value for value in non_null if value.choices is not None)
        if enums and (keyword == "allOf" or len(enums) == len(non_null)):
            choices = list(enums[0].choices or ())
            for enum in enums[1:]:
                if keyword == "allOf":
                    choices = [choice for choice in choices if choice in (enum.choices or ())]
                else:
                    choices.extend(enum.choices or ())
            return replace(
                selected,
                choices=tuple(dict.fromkeys(choices)),
                descriptions=_unique_descriptions(
                    tuple(d for value in non_null for d in value.descriptions)
                ),
            )
        if keyword == "allOf":
            structural = [value for value in alternatives if value.fields or value.items]
            if len(structural) > 1:
                raise ValueError(
                    "Schema descriptions do not support multi-branch structural allOf."
                )
            return replace(
                structural[0] if structural else selected,
                descriptions=_unique_descriptions(
                    tuple(d for value in alternatives for d in value.descriptions)
                ),
            )
        return selected


@dataclass(frozen=True)
class _RenderOptions:
    """Formatting options shared unchanged by every level of the display tree."""

    type_description_prefix: str | None
    cardinality_prefix: str | None
    type_prefix: str | None
    choices_prefix: str | None
    choices_description_prefix: str | None
    component_separator: str
    choices_separator: str
    indent_step: str
    include_field_descriptions: bool


def _render_fields(fields: tuple[_Field, ...], options: _RenderOptions, indent: int) -> list[str]:
    """Render an interpreted tree without inspecting or resolving JSON Schema."""
    lines = []
    prefix = options.indent_step * indent
    for field in fields:
        value = field.value
        # Arrays describe their elements on the field line, retaining item documentation.
        target = value.items if value.type_name == "array" and value.items else value
        descriptions = _unique_descriptions(value.descriptions + target.descriptions)
        type_descriptions = tuple(d for d in descriptions if d.role == "type")
        choice_descriptions = tuple(d for d in descriptions if d.role == "choices")
        components = [f"{prefix}- {field.name}:"]
        if options.include_field_descriptions and field.description:
            components[0] += f" {field.description.text}"
        if options.cardinality_prefix is not None:
            components.append(f"{options.cardinality_prefix}{field.cardinality}")
        if options.type_prefix is not None and target.type_name:
            components.append(f"{options.type_prefix}{target.type_name}")
        if options.choices_prefix is not None and target.choices is not None:
            components.append(
                options.choices_prefix + options.choices_separator.join(target.choices)
            )
        if options.choices_description_prefix is not None and choice_descriptions:
            components.append(
                options.choices_description_prefix
                + options.choices_separator.join(d.text for d in choice_descriptions)
            )
        lines.append(options.component_separator.join(components))
        if options.type_description_prefix is not None:
            lines.extend(
                f"{prefix}{options.indent_step}{options.type_description_prefix}{d.text}"
                for d in type_descriptions
            )
        lines.extend(_render_fields(target.fields, options, indent + 1))
    return lines


def build_schema_description(
    schema: Mapping[str, Any],
    header: str | None = "Feldhinweise und erlaubte Werte (getrennt durch Semikolons):",
    type_description_prefix: str | None = "Beschreibung: ",
    cardinality_prefix: str | None = "Kardinalität: ",
    type_prefix: str | None = "Typ: ",
    choices_prefix: str | None = "Zulässige Werte: ",
    choices_description_prefix: str | None = "Hinweise zu den Werten: ",
    component_separator: str = " | ",
    choices_separator: str = "; ",
    indent_step: str = "  ",
    include_field_descriptions: bool = True,
    include_type_descriptions: bool = True,
    indent: int = 0,
    root_schema: Mapping[str, Any] | None = None,
) -> str:
    """Build a human-readable description with explicit ownership of documentation.

    Property descriptions belong to field lines. Root and nested type descriptions
    belong to `type_description_prefix` lines; enum type descriptions belong to
    `choices_description_prefix`. Array item and non-null branch annotations remain
    attached to their types. A property's own description is never reused as type
    or choice documentation, even when field descriptions are hidden. Shared types
    are documented independently at each field occurrence; equal wording at different
    schema locations is preserved.

    Local references, inline objects, arrays, nullable unions, and enum compositions
    are supported. General structural unions display the first typed non-null branch.
    Enum unions combine choices; enum intersections keep their common choices.
    Cardinality follows the existing display convention: arrays use `0..*`, other
    fields use `0..1` when they have a default, otherwise `1`. This is a prompt
    summary, not a complete JSON Schema validator.

    Args:
        schema: JSON Schema to describe; it is never modified.
        header: Header before the root's fields; None omits it.
        type_description_prefix: Prefix for root/type documentation; None hides it.
        cardinality_prefix: Prefix for cardinalities; None hides them.
        type_prefix: Prefix for type names; None hides them.
        choices_prefix: Prefix for enum choices; None hides them.
        choices_description_prefix: Prefix for enum documentation; None hides it
            independently of the choices themselves, at every nesting level.
        component_separator: Separator between components of a field line.
        choices_separator: Separator between choices and between enum descriptions.
        indent_step: Indentation added for each level of object properties.
        include_field_descriptions: Whether property documentation is shown.
        include_type_descriptions: Deprecated; use type_description_prefix=None.
        indent: Initial indentation (retained for compatibility).
        root_schema: Reference-resolution root when describing a subschema.

    Returns:
        A multiline description of the schema's fields and documentation.

    Raises:
        ValueError: A reference is unresolved or recursive, a type is a list, or a
            structural allOf requires merging multiple branches.
    """
    if not include_type_descriptions:
        type_description_prefix = None
        warn_once(
            "include_type_descriptions is deprecated; please set type_description_prefix to None instead "
            "of using include_type_descriptions=False."
        )
    value = _SchemaInterpreter(root_schema if root_schema is not None else schema).value(schema)
    options = _RenderOptions(
        type_description_prefix,
        cardinality_prefix,
        type_prefix,
        choices_prefix,
        choices_description_prefix,
        component_separator,
        choices_separator,
        indent_step,
        include_field_descriptions,
    )
    lines = []
    if type_description_prefix is not None:
        lines.extend(
            f"{indent_step * indent}{type_description_prefix}{d.text}" for d in value.descriptions
        )
    if header:
        lines.append(header)
    lines.extend(_render_fields(value.fields, options, indent))
    return "\n".join(lines)
