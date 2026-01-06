import copy
import json

from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.utils import build_schema_description, wrap_terminals_with_metadata, \
    METADATA_SCHEMA_WITH_EVIDENCE, METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND
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
    schema_with_metadata = wrap_terminals_with_metadata(schema, metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE)
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.json"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_with_evidence" / fixture_fn
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            json.dump(schema_with_metadata, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema_with_metadata == expected



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
                "properties": {"scientific_name": {"type": ["string", "null"]}},
                "additionalProperties": False,
            },
        },
    }

DEFAULT_METADATA_SCHEMA = METADATA_SCHEMA_WITH_EVIDENCE


def _assert_wrapper(node: dict, *, content_key: str = "content", required_meta: tuple[str, ...] = ("evidence_anchor",)):
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
    _assert_wrapper(out["properties"]["age"])
    assert "anyOf" in out["properties"]["age"]["properties"]["content"]


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
    sci = taxa_def["properties"]["scientific_name"]
    _assert_wrapper(sci)
    assert sci["properties"]["content"] == {"type": ["string", "null"]}


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

    out = wrap_terminals_with_metadata(schema, metadata_schema=meta_props_mapping, content_key="value")

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
