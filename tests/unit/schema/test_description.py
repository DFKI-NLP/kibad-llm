"""Behavioral tests for schema documentation ownership and rendering."""

from copy import deepcopy
from typing import Any

import pytest

from kibad_llm.schema.description import build_schema_description
from kibad_llm.schema.utils import (
    METADATA_SCHEMA_WITH_EVIDENCE,
    wrap_terminals_with_metadata,
)


def _schema(field: dict[str, Any]) -> dict[str, Any]:
    """Place a field in an object schema without introducing extra documentation."""
    return {"type": "object", "properties": {"example": field}}


@pytest.mark.parametrize(
    "field",
    [
        {"type": "string"},
        {"type": "string", "enum": ["A", "B"]},
        {"type": "object", "properties": {"child": {"type": "string"}}},
        {"type": "array", "items": {"type": "string"}},
        {"anyOf": [{"type": "string"}, {"type": "null"}]},
        {"oneOf": [{"type": "null"}, {"type": "string", "enum": ["A", "B"]}]},
    ],
    ids=["scalar", "enum", "object", "array", "anyof", "oneof"],
)
@pytest.mark.parametrize("evidence", [False, True])
@pytest.mark.parametrize("include_field_descriptions", [False, True])
def test_property_description_has_one_owner(field, evidence, include_field_descriptions):
    """Field documentation appears once or is hidden entirely, regardless of wrapping."""
    schema = _schema({**field, "description": " Field\n  instructions. "})
    if evidence:
        schema = wrap_terminals_with_metadata(schema, METADATA_SCHEMA_WITH_EVIDENCE)
    before = deepcopy(schema)
    output = build_schema_description(
        schema, include_field_descriptions=include_field_descriptions
    )
    assert output.count("Field instructions.") == int(include_field_descriptions)
    assert "Beschreibung: Field instructions." not in output
    assert "Hinweise zu den Werten: Field instructions." not in output
    assert schema == before


def test_distinct_field_and_type_annotations_with_equal_text_are_preserved():
    """Source identity, rather than text equality, determines annotation ownership."""
    schema = {
        "type": "object",
        "description": "Root documentation.",
        "properties": {
            name: {"$ref": "#/$defs/Child", "description": "Same wording."}
            for name in ("first", "second")
        },
        "$defs": {
            "Child": {
                "type": "object",
                "description": "Same wording.",
                "properties": {"leaf": {"type": "string", "description": "Leaf instructions."}},
            }
        },
    }
    assert build_schema_description(schema, header=None) == (
        "Beschreibung: Root documentation.\n"
        "- first: Same wording. | Kardinalität: 1 | Typ: object\n"
        "  Beschreibung: Same wording.\n"
        "  - leaf: Leaf instructions. | Kardinalität: 1 | Typ: string\n"
        "- second: Same wording. | Kardinalität: 1 | Typ: object\n"
        "  Beschreibung: Same wording.\n"
        "  - leaf: Leaf instructions. | Kardinalität: 1 | Typ: string"
    )
    hidden = build_schema_description(schema, include_field_descriptions=False)
    assert hidden.count("Same wording.") == 2
    assert "Leaf instructions." not in hidden
    assert "Root documentation." in hidden


@pytest.mark.parametrize("evidence", [False, True])
def test_array_item_and_nullable_branch_descriptions_are_preserved(evidence):
    """Descriptions on distinct item/branch schemas are type documentation."""
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "List instructions.",
                "items": {"type": "string", "description": "Item documentation."},
            },
            "optional": {
                "description": "Field instructions.",
                "anyOf": [
                    {"type": "null"},
                    {"type": "string", "description": "Branch documentation."},
                ],
            },
        },
    }
    if evidence:
        schema = wrap_terminals_with_metadata(schema, METADATA_SCHEMA_WITH_EVIDENCE)
    output = build_schema_description(schema, include_field_descriptions=False)
    assert "instructions." not in output
    assert output.count("Beschreibung: Item documentation.") == 1
    assert output.count("Beschreibung: Branch documentation.") == 1


def test_nested_type_descriptions_survive_inline_field_description_removal():
    """Suppressing one field's duplicate must not suppress documentation deeper in its tree."""
    schema = _schema(
        {
            "type": "object",
            "description": "Inline field instructions.",
            "properties": {"nested": {"$ref": "#/$defs/Nested"}},
        }
    )
    schema["$defs"] = {
        "Nested": {"type": "object", "description": "Nested type.", "properties": {}}
    }
    output = build_schema_description(schema)
    assert output.count("Inline field instructions.") == 1
    assert "    Beschreibung: Nested type." in output


@pytest.mark.parametrize("keyword", ["anyOf", "oneOf", "allOf"])
def test_enum_composition_preserves_sources_and_combines_choices(keyword):
    """Choice documentation survives composition and is not confused with field instructions."""
    schema = _schema(
        {
            "description": "Choose a value.",
            keyword: [
                {"$ref": "#/$defs/A"},
                {"$ref": "#/$defs/A"},
                {"$ref": "#/$defs/B"},
            ],
        }
    )
    schema["$defs"] = {
        "A": {"type": "string", "enum": ["A", "B"], "description": "Choice documentation."},
        "B": {"type": "string", "enum": ["B", "C"], "description": "Choice documentation."},
    }
    output = build_schema_description(schema, header=None)
    choices = "B" if keyword == "allOf" else "A; B; C"
    assert output == (
        f"- example: Choose a value. | Kardinalität: 1 | Typ: string | Zulässige Werte: {choices}"
        " | Hinweise zu den Werten: Choice documentation.; Choice documentation."
    )


def test_empty_enum_intersection_stays_empty():
    """An empty intersection must not be repopulated by a later branch."""
    schema = _schema(
        {"allOf": [{"type": "string", "enum": [choice]} for choice in ("A", "B", "A")]}
    )
    assert build_schema_description(schema, header=None).endswith("Zulässige Werte: ")


def test_nullable_enum_without_explicit_type_uses_the_non_null_branch():
    """Enums need not include a type keyword to retain their choices and documentation."""
    schema = _schema({"anyOf": [{"type": "null"}, {"enum": ["A"], "description": "Enum notes."}]})
    output = build_schema_description(schema)
    assert "Typ: null" not in output
    assert "Zulässige Werte: A | Hinweise zu den Werten: Enum notes." in output


def test_allof_type_constraint_preserves_object_properties_and_documentation():
    """A separate type constraint does not replace the branch containing properties."""
    schema = _schema(
        {
            "allOf": [
                {"type": "object", "description": "Object documentation."},
                {
                    "properties": {
                        "child": {"type": "string", "description": "Child instructions."}
                    }
                },
            ]
        }
    )
    output = build_schema_description(schema)
    assert output.count("Beschreibung: Object documentation.") == 1
    assert "- child: Child instructions." in output


def test_multi_branch_structural_allof_fails_explicitly():
    """Object intersections requiring a property merge must not silently lose fields."""
    schema = _schema({"allOf": [_schema({"type": "string"}), _schema({"type": "integer"})]})
    with pytest.raises(ValueError, match="multi-branch structural allOf"):
        build_schema_description(schema)


def test_shared_enum_documentation_is_repeated_per_field_occurrence():
    """Each use of a shared enum retains its documentation independently."""
    schema = {
        "type": "object",
        "properties": {name: {"$ref": "#/$defs/Enum"} for name in ("first", "second")},
        "$defs": {"Enum": {"type": "string", "enum": ["A"], "description": "Enum notes."}},
    }
    output = build_schema_description(schema)
    assert output.count("Hinweise zu den Werten: Enum notes.") == 2


def test_reference_chain_preserves_field_item_and_enum_documentation():
    """Array type documentation stays separate from its element enum's documentation."""
    schema = _schema({"$ref": "#/$defs/Items", "description": "Field instructions."})
    schema["$defs"] = {
        "Items": {
            "type": "array",
            "description": "Array documentation.",
            "items": {"$ref": "#/$defs/Alias", "description": "Item documentation."},
        },
        "Alias": {"$ref": "#/$defs/Enum", "description": "Alias documentation."},
        "Enum": {"type": "string", "enum": ["A"], "description": "Enum documentation."},
    }
    output = build_schema_description(schema, header=None)
    assert output == (
        "- example: Field instructions. | Kardinalität: 0..* | Typ: string | Zulässige Werte: A"
        " | Hinweise zu den Werten: Item documentation.; Alias documentation.; Enum documentation.\n"
        "  Beschreibung: Array documentation."
    )


def test_formatting_options_apply_at_every_level():
    """Nested enum notes honor the same prefixes and separators as the root's fields."""
    schema = _schema(
        {
            "type": "object",
            "description": "Field instructions.",
            "properties": {"child": {"$ref": "#/$defs/Enum"}},
        }
    )
    schema["$defs"] = {
        "Enum": {"type": "string", "enum": ["A", "B"], "description": "Enum notes."}
    }
    assert build_schema_description(
        schema,
        header=None,
        type_prefix="T=",
        cardinality_prefix=None,
        choices_prefix="C=",
        choices_description_prefix="N=",
        component_separator=" / ",
        choices_separator=", ",
        indent_step="....",
    ) == (
        "- example: Field instructions. / T=object\n"
        "....- child: / T=string / C=A, B / N=Enum notes."
    )
    assert "Enum notes." not in build_schema_description(schema, choices_description_prefix=None)
    assert "Enum notes." in build_schema_description(schema, choices_prefix=None)


@pytest.mark.parametrize(
    "hide_types", [{"type_description_prefix": None}, {"include_type_descriptions": False}]
)
def test_hiding_type_descriptions_keeps_field_and_enum_documentation(hide_types):
    """Field, type, and choice documentation have independent visibility controls."""
    schema = _schema({"$ref": "#/$defs/Object", "description": "Field instructions."})
    schema["description"] = "Root documentation."
    schema["$defs"] = {
        "Object": {
            "type": "object",
            "description": "Object documentation.",
            "properties": {"child": {"$ref": "#/$defs/Enum"}},
        },
        "Enum": {"type": "string", "enum": ["A"], "description": "Enum notes."},
    }
    output = build_schema_description(schema, **hide_types)
    assert "documentation." not in output
    assert "Field instructions." in output
    assert "Enum notes." in output


def test_evidence_content_description_is_independent_of_field_instructions():
    """Explicit content documentation and evidence metadata are still rendered once."""
    schema = wrap_terminals_with_metadata(
        _schema({"type": "string", "description": "Field instructions."}),
        METADATA_SCHEMA_WITH_EVIDENCE,
        content_description="Extracted value.",
    )
    output = build_schema_description(schema)
    assert output.count("Field instructions.") == 1
    assert output.count("Extracted value.") == 1
    assert "- evidence_anchor:" in output


def test_escaped_reference_and_single_branch_allof():
    """A definition's identity is its decoded pointer, including escaped name characters."""
    schema = _schema(
        {"allOf": [{"$ref": "#/$defs/With~1slash~0tilde"}], "description": "Field instructions."}
    )
    schema["$defs"] = {
        "With/slash~tilde": {
            "type": "object",
            "description": "Type documentation.",
            "properties": {},
        }
    }
    output = build_schema_description(schema)
    assert output.count("Field instructions.") == 1
    assert output.count("Beschreibung: Type documentation.") == 1


@pytest.mark.parametrize("ref", ["#/$defs/Missing", "https://example.org/schema.json"])
def test_unresolvable_reference_fails_explicitly(ref):
    """Incomplete schema descriptions must not silently omit referenced documentation."""
    with pytest.raises(ValueError, match="Cannot resolve schema reference"):
        build_schema_description(_schema({"$ref": ref}))


def test_recursive_reference_fails_explicitly():
    """Recursive schemas produce a useful error rather than infinite expansion."""
    with pytest.raises(ValueError, match="Recursive schema"):
        build_schema_description(_schema({"$ref": "#"}))
