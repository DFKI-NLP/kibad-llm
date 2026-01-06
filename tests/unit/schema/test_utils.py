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


def test_schema_should_be_wrapped_terminal_scalars_and_scalar_lists() -> None:
    root: dict[str, Any] = {}

    # plain scalar: string
    assert _schema_should_be_wrapped(root, {"type": "string"}) is True

    # plain scalar: integer
    assert _schema_should_be_wrapped(root, {"type": "integer"}) is True

    # plain scalar: number
    assert _schema_should_be_wrapped(root, {"type": "number"}) is True

    # plain scalar: boolean
    assert _schema_should_be_wrapped(root, {"type": "boolean"}) is True

    # scalar: null
    assert _schema_should_be_wrapped(root, {"type": "null"}) is False

    # list-of-types incl. null (common Optional pattern)
    assert _schema_should_be_wrapped(root, {"type": ["string", "null"]}) is False


def test_schema_should_be_wrapped_terminal_enum_and_const() -> None:
    root: dict[str, Any] = {}

    # inline enum
    assert _schema_should_be_wrapped(root, {"type": "string", "enum": ["A", "B"]}) is True

    # const (non-null)
    assert _schema_should_be_wrapped(root, {"const": 123}) is True

    # const (null)
    assert _schema_should_be_wrapped(root, {"const": None}) is False


def test_schema_should_be_wrapped_non_terminals_object_and_array() -> None:
    root: dict[str, Any] = {}

    # object is not terminal
    assert (
        _schema_should_be_wrapped(
            root, {"type": "object", "properties": {"x": {"type": "string"}}}
        )
        is False
    )

    # array is not terminal
    assert _schema_should_be_wrapped(root, {"type": "array", "items": {"type": "string"}}) is False


def test_schema_should_be_wrapped_unions_anyof_oneof_allof() -> None:
    root: dict[str, Any] = {}

    # anyOf: nullable scalar union
    assert (
        _schema_should_be_wrapped(root, {"anyOf": [{"type": "integer"}, {"type": "null"}]})
        is False
    )

    # oneOf: nullable scalar union
    assert (
        _schema_should_be_wrapped(root, {"oneOf": [{"type": "string"}, {"type": "null"}]}) is False
    )

    # anyOf: includes object -> not terminal
    assert (
        _schema_should_be_wrapped(
            root, {"anyOf": [{"type": "string"}, {"type": "object", "properties": {}}]}
        )
        is False
    )

    # oneOf: includes array -> not terminal
    assert (
        _schema_should_be_wrapped(
            root, {"oneOf": [{"type": "null"}, {"type": "array", "items": {"type": "string"}}]}
        )
        is False
    )

    # allOf: scalar constraints only -> terminal
    assert (
        _schema_should_be_wrapped(root, {"allOf": [{"type": "string"}, {"minLength": 2}]}) is True
    )

    # allOf: includes object -> not terminal
    assert (
        _schema_should_be_wrapped(
            root, {"allOf": [{"type": "string"}, {"type": "object", "properties": {}}]}
        )
        is False
    )

    assert (
        _schema_should_be_wrapped(
            root,
            {
                # field can be either a scalar (string) OR an object with an integer field
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {"x": {"type": "integer"}},
                        "additionalProperties": False,
                    },
                ]
            },
        )
        is False
    )


def test_schema_should_be_wrapped_refs_to_defs_terminal_vs_non_terminal_and_nullable_ref_union() -> (
    None
):
    # $ref to enum def -> terminal
    root_enum = {"$defs": {"HabitatEnum": {"type": "string", "enum": ["A", "B"]}}}
    assert _schema_should_be_wrapped(root_enum, {"$ref": "#/$defs/HabitatEnum"}) is True

    # $ref to object def -> not terminal
    root_obj = {
        "$defs": {
            "Taxa": {
                "type": "object",
                "properties": {"scientific_name": {"type": ["string", "null"]}},
                "additionalProperties": False,
            }
        }
    }
    assert _schema_should_be_wrapped(root_obj, {"$ref": "#/$defs/Taxa"}) is False

    # Optional[Enum]-style union (anyOf: enum ref + null) -> not a terminal
    assert (
        _schema_should_be_wrapped(
            root_enum,
            {"anyOf": [{"$ref": "#/$defs/HabitatEnum"}, {"type": "null"}], "default": None},
        )
        is False
    )


def test_wrap_terminals_with_metadata_anyof_scalar_or_object():
    schema = {
        "type": "object",
        "properties": {
            "mixed": {
                # field can be either a scalar (string) OR an object with an integer field
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

    metadata_schema = {
        "evidence_anchor": {
            "type": "string",
            "description": "Verbatim excerpt from the source text supporting the extracted content.",
        }
    }
    out = wrap_terminals_with_metadata(schema, metadata_schema=metadata_schema)

    assert out == {
        "type": "object",
        "properties": {
            "mixed": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "evidence_anchor": {
                                "type": "string",
                                "description": "Verbatim excerpt from the source text supporting the extracted content.",
                            },
                        },
                        "required": ["content", "evidence_anchor"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "x": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "integer"},
                                    "evidence_anchor": {
                                        "type": "string",
                                        "description": "Verbatim excerpt from the source text supporting the extracted content.",
                                    },
                                },
                                "required": ["content", "evidence_anchor"],
                                "additionalProperties": False,
                            }
                        },
                        "additionalProperties": False,
                    },
                ]
            }
        },
    }


def test_wrap_terminals_with_metadata_anyof_scalar_or_null():
    schema = {
        "type": "object",
        "properties": {
            "mixed": {
                # field can be either a scalar (string) OR null
                "anyOf": [{"type": "string"}, {"type": "null"}]
            }
        },
    }
    metadata_schema = {
        "evidence_anchor": {
            "type": "string",
            "description": "Verbatim excerpt from the source text supporting the extracted content.",
        }
    }
    out = wrap_terminals_with_metadata(schema, metadata_schema=metadata_schema)
    assert out == {
        "type": "object",
        "properties": {
            "mixed": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "evidence_anchor": {
                                "type": "string",
                                "description": "Verbatim excerpt from the source text supporting the extracted content.",
                            },
                        },
                        "required": ["content", "evidence_anchor"],
                        "additionalProperties": False,
                    },
                    {"type": "null"},
                ]
            }
        },
    }


@pytest.fixture
def sample_schema() -> dict:
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
            # terminal def (must NOT be wrapped at the def root)
            "HabitatEnum": {"type": "string", "enum": ["A", "B"]},
            # object def (root must NOT be wrapped, but its terminal fields should be)
            "Taxa": {
                "type": "object",
                "properties": {
                    "scientific_name": {"anyOf": [{"type": "string"}, {"type": "null"}]}
                },
                "additionalProperties": False,
            },
        },
    }


DEFAULT_METADATA_SCHEMA = METADATA_SCHEMA_WITH_EVIDENCE


def _assert_wrapper(
    node: dict,
    *,
    content_key: str = "content",
    required_meta: tuple[str, ...] = ("evidence_anchor",),
):
    assert node["type"] == "object"
    assert node.get("additionalProperties") is False

    props = node["properties"]
    assert content_key in props
    for k in required_meta:
        assert k in props

    req = node.get("required", [])
    assert content_key in req
    for k in required_meta:
        assert k in req


def test_wraps_terminal_properties_and_is_pure(sample_schema):
    schema = sample_schema
    schema_before = copy.deepcopy(schema)

    out = wrap_terminals_with_metadata(schema, metadata_schema=DEFAULT_METADATA_SCHEMA)

    # purity / no mutation
    assert schema == schema_before

    # name (string) wrapped
    _assert_wrapper(out["properties"]["name"])
    assert out["properties"]["name"]["properties"]["content"] == {"type": "string"}

    # age (nullable union) wrapped; content preserves anyOf
    assert schema["properties"]["age"] == {"anyOf": [{"type": "integer"}, {"type": "null"}]}
    assert out["properties"]["age"] == {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "content": {"type": "integer"},
                    "evidence_anchor": {
                        "type": "string",
                        "description": "Verbatim excerpt from the source text supporting the extracted content.",
                    },
                },
                "required": ["content", "evidence_anchor"],
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    }


def test_wraps_array_items_but_not_array_node(sample_schema):
    out = wrap_terminals_with_metadata(sample_schema, metadata_schema=DEFAULT_METADATA_SCHEMA)

    tags = out["properties"]["tags"]
    assert tags["type"] == "array"  # not wrapped
    _assert_wrapper(tags["items"])  # items wrapped
    assert tags["items"]["properties"]["content"] == {"type": "string"}


def test_does_not_wrap_defs_roots_but_wraps_terminals_inside_object_defs(sample_schema):
    out = wrap_terminals_with_metadata(sample_schema, metadata_schema=DEFAULT_METADATA_SCHEMA)

    # terminal def root unchanged
    assert out["$defs"]["HabitatEnum"] == {"type": "string", "enum": ["A", "B"]}

    # object def root unchanged, but its terminal fields wrapped
    taxa_def = out["$defs"]["Taxa"]
    assert taxa_def["type"] == "object"
    assert sample_schema["$defs"]["Taxa"]["properties"]["scientific_name"] == {
        "anyOf": [{"type": "string"}, {"type": "null"}],
    }
    assert taxa_def["properties"]["scientific_name"] == {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "evidence_anchor": {
                        "type": "string",
                        "description": "Verbatim excerpt from the source text supporting the extracted content.",
                    },
                },
                "required": ["content", "evidence_anchor"],
                "additionalProperties": False,
            },
            {"type": "null"},
        ]
    }


def test_wraps_ref_to_terminal_def_as_content_ref(sample_schema):
    out = wrap_terminals_with_metadata(sample_schema, metadata_schema=DEFAULT_METADATA_SCHEMA)

    enum_ref = out["properties"]["enum_ref"]
    _assert_wrapper(enum_ref)
    assert enum_ref["properties"]["content"] == {"$ref": "#/$defs/HabitatEnum"}


def test_custom_metadata_and_content_key(sample_schema):
    schema = sample_schema
    meta_props_mapping = {
        "evidence_anchor": {"type": "string"},
        "confidence_score": {"type": "number"},
    }

    out = wrap_terminals_with_metadata(
        schema, metadata_schema=meta_props_mapping, content_key="value"
    )

    node = out["properties"]["name"]
    # metadata mapping -> no required meta fields by default (only "value" required)
    _assert_wrapper(node, content_key="value", required_meta=())
    assert "evidence_anchor" in node["properties"]
    assert "confidence_score" in node["properties"]
    assert node["properties"]["value"] == {"type": "string"}


def test_wrap_terminals_with_metadata_is_idempotent(sample_schema):
    schema = sample_schema

    once = wrap_terminals_with_metadata(schema, metadata_schema=DEFAULT_METADATA_SCHEMA)
    twice = wrap_terminals_with_metadata(once, metadata_schema=DEFAULT_METADATA_SCHEMA)

    assert twice == once


def test_wrapped_terminal_not_wrapped_again_inside_content(sample_schema):
    once = wrap_terminals_with_metadata(sample_schema, metadata_schema=DEFAULT_METADATA_SCHEMA)

    name = once["properties"]["name"]
    # content should still be the original terminal schema, not another wrapper
    assert name["properties"]["content"] == {"type": "string"}


def test_metadata_schema_shorthand_equals_full(sample_schema):
    schema = sample_schema

    meta_full = METADATA_SCHEMA_WITH_EVIDENCE
    meta_shorthand = METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND

    out_full = wrap_terminals_with_metadata(schema, metadata_schema=meta_full)
    out_short = wrap_terminals_with_metadata(schema, metadata_schema=meta_shorthand)

    assert out_short == out_full
