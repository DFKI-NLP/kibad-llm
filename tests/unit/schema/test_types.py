import json

from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from tests.conftest import WRITE_FIXTURE_DATA
from tests.unit.schema import (
    ALL_COMPOUNDS,
    ALL_MODELS,
    camel_case_to_snake_case,
)


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_models(model_cls: type[BaseModel]):
    schema = model_cls.model_json_schema(by_alias=False)
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.json"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema" / fixture_fn
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema == expected


@pytest.mark.parametrize("model_cls", list(ALL_COMPOUNDS))
def test_compound_models(model_cls: type[BaseModel]):
    schema = model_cls.model_json_schema(by_alias=False)
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.json"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_compound" / fixture_fn
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema == expected
