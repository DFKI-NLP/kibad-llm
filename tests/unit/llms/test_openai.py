import copy
import json

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    MessageRole,
    TextBlock,
    ThinkingBlock,
)
from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.llms.base import ReasoningExtractionError
from kibad_llm.llms.openai import OpenAI, make_openai_strict_json_schema
from tests.conftest import WRITE_FIXTURE_DATA
from tests.unit.schema import (
    ALL_MODELS,
    camel_case_to_snake_case,
)


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_make_openai_strict_json_for_models(model_cls: type[BaseModel]):
    # schema = model_cls.model_json_schema(by_alias=False)
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.json"
    path_schema = PROJ_ROOT / "tests" / "fixtures" / "schema" / fixture_fn
    # load schema from fixture
    with open(path_schema) as f:
        schema = json.load(f)

    result = make_openai_strict_json_schema(schema)

    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_strict" / fixture_fn
    if WRITE_FIXTURE_DATA:
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert result == expected


def test_object_gets_required_and_additional_properties_false() -> None:
    schema = {
        "type": "object",
        "properties": {
            "b": {"type": "string"},
            "a": {"type": "integer"},
        },
    }

    patched = make_openai_strict_json_schema(schema)

    # required must include every property key (and preserve order of properties)
    assert patched["required"] == ["b", "a"]
    # strict mode requires forbidding extra keys
    assert patched["additionalProperties"] is False


def test_removes_default_everywhere() -> None:
    schema = {
        "type": "object",
        "properties": {
            "x": {"type": "string", "default": "hello"},
            "y": {
                "type": "object",
                "properties": {"z": {"type": "integer", "default": 7}},
            },
        },
    }

    patched = make_openai_strict_json_schema(schema)

    assert "default" not in patched["properties"]["x"]
    assert "default" not in patched["properties"]["y"]["properties"]["z"]


def test_ref_with_sibling_keywords_is_moved_into_anyof() -> None:
    schema = {
        "type": "object",
        "properties": {
            "species_group": {
                "$ref": "#/$defs/SpeciesGroupEnum",
                "description": "Taxonomische Gruppe der Art",
            }
        },
        "$defs": {
            "SpeciesGroupEnum": {"type": "string", "enum": ["A", "B"]},
        },
    }

    patched = make_openai_strict_json_schema(schema)
    prop = patched["properties"]["species_group"]

    assert "$ref" not in prop
    assert prop["anyOf"][0] == {"$ref": "#/$defs/SpeciesGroupEnum"}
    assert prop["description"] == "Taxonomische Gruppe der Art"


def test_ref_is_prepended_when_anyof_already_exists() -> None:
    schema = {
        "type": "object",
        "properties": {
            "term": {
                "anyOf": [{"type": "null"}],
                "$ref": "#/$defs/TermEnum",
                "description": "some desc",
            }
        },
        "$defs": {"TermEnum": {"type": "string", "enum": ["X", "Y"]}},
    }

    patched = make_openai_strict_json_schema(schema)
    term = patched["properties"]["term"]

    assert "$ref" not in term
    assert term["anyOf"][0] == {"$ref": "#/$defs/TermEnum"}
    assert {"type": "null"} in term["anyOf"]
    assert term["description"] == "some desc"


def test_ref_without_siblings_is_left_as_ref() -> None:
    schema = {"$ref": "#/$defs/Foo"}

    patched = make_openai_strict_json_schema(schema)

    assert patched["$ref"] == "#/$defs/Foo"


def test_ref_with_defs_sibling_is_rewritten_to_anyof() -> None:
    schema = {"$ref": "#/$defs/Foo", "$defs": {"Foo": {"type": "string"}}}

    patched = make_openai_strict_json_schema(schema)

    assert "$ref" not in patched
    assert patched["anyOf"][0] == {"$ref": "#/$defs/Foo"}
    assert patched["$defs"] == {"Foo": {"type": "string"}}


def test_patches_defs_objects_recursively() -> None:
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"$ref": "#/$defs/Thing"}}},
        "$defs": {
            "Thing": {
                "type": "object",
                "properties": {"name": {"type": "string", "default": "n/a"}},
            }
        },
    }

    patched = make_openai_strict_json_schema(schema)
    thing = patched["$defs"]["Thing"]

    assert thing["required"] == ["name"]
    assert thing["additionalProperties"] is False
    assert "default" not in thing["properties"]["name"]


def test_does_not_mutate_input_schema() -> None:
    schema = {
        "type": "object",
        "properties": {
            "x": {"type": "string", "default": "hello"},
            "y": {"$ref": "#/$defs/Y", "description": "desc"},
        },
        "$defs": {"Y": {"type": "string"}},
    }
    original = copy.deepcopy(schema)

    _ = make_openai_strict_json_schema(schema)

    assert schema == original, "make_openai_strict_json_schema must not mutate its input"


def _response(*blocks) -> ChatResponse:
    """Return a chat response with the given content blocks."""
    return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, blocks=list(blocks)))


def test_get_reasoning_returns_summary() -> None:
    """Join the contents of all thinking blocks."""
    llm = OpenAI(model="gpt-5", api_key="test", reasoning_options={"summary": "auto"})
    response = _response(
        ThinkingBlock(content="first"), ThinkingBlock(content="second"), TextBlock(text="{}")
    )

    assert llm.get_reasoning_from_chat_response(response) == "first\n\nsecond"


def test_get_reasoning_without_summary_when_summaries_are_enabled() -> None:
    """The API can omit the summary for a response, which is not an error."""
    llm = OpenAI(model="gpt-5", api_key="test", reasoning_options={"summary": "auto"})

    assert llm.get_reasoning_from_chat_response(_response(TextBlock(text="{}"))) is None


def test_get_reasoning_without_summary_when_summaries_are_disabled() -> None:
    """Without enabled summaries, a missing summary points to a configuration error."""
    llm = OpenAI(model="gpt-5", api_key="test")

    with pytest.raises(ReasoningExtractionError, match="reasoning_options.summary"):
        llm.get_reasoning_from_chat_response(_response(TextBlock(text="{}")))
