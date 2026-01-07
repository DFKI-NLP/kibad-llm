import copy
import json
from typing import Any

from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.utils import (
    METADATA_SCHEMA_WITH_EVIDENCE,
    METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND,
    _schema_should_be_wrapped,
    build_schema_description,
    wrap_terminals_with_metadata,
)
from tests.conftest import WRITE_FIXTURE_DATA
from tests.unit.schema import (
    ALL_COMPOUNDS,
    ALL_MODELS,
    camel_case_to_snake_case,
)


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_build_schema_description(model_cls: type[BaseModel]):
    description = build_schema_description(model_cls.model_json_schema(by_alias=False))
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.txt"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_description" / fixture_fn
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected


@pytest.mark.parametrize("model_cls", list(ALL_COMPOUNDS))
def test_build_schema_description_compound(model_cls: type[BaseModel]):
    # dont include header for compound features
    description = build_schema_description(
        model_cls.model_json_schema(by_alias=False), header=None
    )
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.txt"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_compound_description" / fixture_fn
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_wrap_terminals_with_metadata_evidence(model_cls: type[BaseModel]):
    schema = model_cls.model_json_schema(by_alias=False)
    schema_with_metadata = wrap_terminals_with_metadata(
        schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.json"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_with_evidence" / fixture_fn
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            json.dump(schema_with_metadata, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema_with_metadata == expected


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_wrap_terminals_with_metadata_evidence_and_build_schema_description(
    model_cls: type[BaseModel],
):
    schema = model_cls.model_json_schema(by_alias=False)
    schema_with_metadata = wrap_terminals_with_metadata(
        schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )
    description = build_schema_description(schema_with_metadata)
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.txt"
    path_expected = (
        PROJ_ROOT / "tests" / "fixtures" / "schema_description_with_evidence" / fixture_fn
    )
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _assert_is_wrapper(
    node: dict[str, Any],
    *,
    content_schema: dict[str, Any],
    content_key: str = "content",
    required_meta: tuple[str, ...] = ("evidence_anchor",),
) -> None:
    """Assert that `node` is a wrapper object with expected content schema and required metadata."""
    assert node["type"] == "object"
    assert node.get("additionalProperties") is False

    props = node["properties"]
    assert props[content_key] == content_schema
    for k in required_meta:
        assert k in props

    req = set(node.get("required", []))
    assert content_key in req
    for k in required_meta:
        assert k in req


def _find_wrapped_branch(union_node: dict[str, Any]) -> dict[str, Any]:
    """Return the first anyOf/oneOf branch that looks like our wrapper."""
    for key in ("anyOf", "oneOf"):
        branches = union_node.get(key)
        if isinstance(branches, list):
            for b in branches:
                if (
                    isinstance(b, dict)
                    and b.get("type") == "object"
                    and "properties" in b
                    and "content" in b["properties"]
                ):
                    return b
    raise AssertionError("No wrapped branch found in union node.")


# ---------------------------------------------------------------------------
# _schema_should_be_wrapped: policy-level unit tests
# ---------------------------------------------------------------------------


def test_schema_should_be_wrapped_value_schemas() -> None:
    root: dict[str, Any] = {}

    # plain scalars are wrapped
    assert _schema_should_be_wrapped(root, {"type": "string"}) is True
    assert _schema_should_be_wrapped(root, {"type": "integer"}) is True
    assert _schema_should_be_wrapped(root, {"type": "number"}) is True
    assert _schema_should_be_wrapped(root, {"type": "boolean"}) is True

    # inline enum + non-null const are wrapped
    assert _schema_should_be_wrapped(root, {"type": "string", "enum": ["A", "B"]}) is True
    assert _schema_should_be_wrapped(root, {"const": 123}) is True


def test_schema_should_be_wrapped_excludes_null_structural_and_unions() -> None:
    root: dict[str, Any] = {}

    # null alone must NOT be wrapped (otherwise we'd allow "metadata without content")
    assert _schema_should_be_wrapped(root, {"type": "null"}) is False
    assert _schema_should_be_wrapped(root, {"const": None}) is False

    # structural schemas are not wrapped (their children are handled recursively)
    assert (
        _schema_should_be_wrapped(
            root, {"type": "object", "properties": {"x": {"type": "string"}}}
        )
        is False
    )
    assert _schema_should_be_wrapped(root, {"type": "array", "items": {"type": "string"}}) is False

    # unions (anyOf/oneOf) are not wrapped at the root; we wrap their branches
    assert (
        _schema_should_be_wrapped(root, {"anyOf": [{"type": "string"}, {"type": "null"}]}) is False
    )
    assert (
        _schema_should_be_wrapped(root, {"oneOf": [{"type": "string"}, {"type": "null"}]}) is False
    )

    # allOf: scalar constraints only => treated as wrappable value schema
    assert (
        _schema_should_be_wrapped(root, {"allOf": [{"type": "string"}, {"minLength": 2}]}) is True
    )

    # allOf including object/array-ish => not wrappable
    assert (
        _schema_should_be_wrapped(
            root, {"allOf": [{"type": "string"}, {"type": "object", "properties": {}}]}
        )
        is False
    )


def test_schema_should_be_wrapped_refs() -> None:
    # $ref to enum def => wrappable
    root_enum = {"$defs": {"HabitatEnum": {"type": "string", "enum": ["A", "B"]}}}
    assert _schema_should_be_wrapped(root_enum, {"$ref": "#/$defs/HabitatEnum"}) is True

    # $ref to object def => not wrappable
    root_obj = {"$defs": {"Taxa": {"type": "object", "properties": {"x": {"type": "string"}}}}}
    assert _schema_should_be_wrapped(root_obj, {"$ref": "#/$defs/Taxa"}) is False


# ---------------------------------------------------------------------------
# wrap_terminals_with_metadata: behavior tests (critical transformations)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
            "tags": {"type": "array", "items": {"type": "string"}},
            "obj": {"type": "object", "properties": {"x": {"type": "number"}}},
            "enum_ref": {"$ref": "#/$defs/HabitatEnum"},
        },
        "$defs": {
            # terminal def: must NOT be wrapped at the def root
            "HabitatEnum": {"type": "string", "enum": ["A", "B"]},
            # object def root: must NOT be wrapped, but its terminal children should
            "Taxa": {
                "type": "object",
                "properties": {
                    "scientific_name": {"anyOf": [{"type": "string"}, {"type": "null"}]}
                },
                "additionalProperties": False,
            },
        },
    }


def test_wrap_terminals_with_metadata_is_pure_and_wraps_simple_property(sample_schema) -> None:
    schema_before = copy.deepcopy(sample_schema)
    out = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )

    # input is not mutated
    assert sample_schema == schema_before

    # name: string => wrapper
    _assert_is_wrapper(out["properties"]["name"], content_schema={"type": "string"})


def test_wrap_terminals_with_metadata_anyof_scalar_or_null_wraps_only_scalar_branch() -> None:
    schema = {
        "type": "object",
        "properties": {"mixed": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
    }
    out = wrap_terminals_with_metadata(schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE)

    # union preserved
    mixed = out["properties"]["mixed"]
    assert "anyOf" in mixed

    # string branch wrapped, null branch unchanged
    wrapped = _find_wrapped_branch(mixed)
    _assert_is_wrapper(wrapped, content_schema={"type": "string"})
    assert {"type": "null"} in mixed["anyOf"]


def test_wrap_terminals_with_metadata_anyof_scalar_or_object_wraps_scalar_branch_and_object_leaves() -> (
    None
):
    schema = {
        "type": "object",
        "properties": {
            "mixed": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {"x": {"type": "integer"}},
                        "additionalProperties": False,
                    },
                ]
            }
        },
    }
    out = wrap_terminals_with_metadata(schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE)

    mixed = out["properties"]["mixed"]
    assert "anyOf" in mixed and len(mixed["anyOf"]) == 2

    # scalar branch wrapped
    scalar_branch = mixed["anyOf"][0]
    _assert_is_wrapper(scalar_branch, content_schema={"type": "string"})

    # object branch not wrapped as a whole, but its leaf x is wrapped
    obj_branch = mixed["anyOf"][1]
    assert obj_branch["type"] == "object"
    assert obj_branch.get("additionalProperties") is False
    _assert_is_wrapper(obj_branch["properties"]["x"], content_schema={"type": "integer"})


def test_wrap_terminals_with_metadata_wraps_array_items_but_not_array_node(sample_schema) -> None:
    out = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )

    tags = out["properties"]["tags"]
    assert tags["type"] == "array"  # array node stays array
    _assert_is_wrapper(tags["items"], content_schema={"type": "string"})  # items wrapped


def test_wrap_terminals_with_metadata_defs_roots_unchanged_but_children_wrapped(
    sample_schema,
) -> None:
    out = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )

    # terminal def root unchanged
    assert out["$defs"]["HabitatEnum"] == {"type": "string", "enum": ["A", "B"]}

    # object def root unchanged, but its terminal child is wrapped (and nullable union is preserved)
    taxa = out["$defs"]["Taxa"]
    assert taxa["type"] == "object"

    sci_name = taxa["properties"]["scientific_name"]
    assert "anyOf" in sci_name
    wrapped = _find_wrapped_branch(sci_name)
    _assert_is_wrapper(wrapped, content_schema={"type": "string"})
    assert {"type": "null"} in sci_name["anyOf"]


def test_wrap_terminals_with_metadata_wraps_ref_to_terminal_def_as_content_ref(
    sample_schema,
) -> None:
    out = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )

    enum_ref = out["properties"]["enum_ref"]
    _assert_is_wrapper(enum_ref, content_schema={"$ref": "#/$defs/HabitatEnum"})


def test_wrap_terminals_with_metadata_metadata_shorthand_equals_full(sample_schema) -> None:
    out_full = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )
    out_short = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND
    )
    assert out_short == out_full


def test_wrap_terminals_with_metadata_idempotent(sample_schema) -> None:
    once = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE
    )
    twice = wrap_terminals_with_metadata(once, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE)
    assert twice == once


def test_wrap_terminals_with_metadata_custom_content_key_and_metadata_requirements(
    sample_schema,
) -> None:
    # "properties mapping" shorthand => keys become required (by your normalization rule)
    meta_props_mapping = {
        "evidence_anchor": {"type": "string"},
        "confidence_score": {"type": "number"},
    }
    out = wrap_terminals_with_metadata(
        sample_schema, metadata_schema=meta_props_mapping, content_key="value"
    )

    name = out["properties"]["name"]
    _assert_is_wrapper(
        name,
        content_schema={"type": "string"},
        content_key="value",
        required_meta=("evidence_anchor", "confidence_score"),
    )
