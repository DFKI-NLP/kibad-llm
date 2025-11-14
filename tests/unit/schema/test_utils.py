from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.utils import build_schema_description
from tests.conftest import WRITE_FIXTURE_DATA
from tests.unit.schema import (
    ALL_COMPOUND_FEATURES,
    ALL_MODELS,
    camel_case_to_snake_case,
)


@pytest.mark.parametrize("model_cls", list(ALL_MODELS))
def test_build_schema_description(model_cls: type[BaseModel]):
    description = build_schema_description(model_cls.model_json_schema(by_alias=False))
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.txt"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_description" / fixture_fn
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected


@pytest.mark.parametrize("model_cls", list(ALL_COMPOUND_FEATURES))
def test_build_schema_description_compound_feature(model_cls: type[BaseModel]):
    # dont include header for compound features
    description = build_schema_description(
        model_cls.model_json_schema(by_alias=False), header=None
    )
    fixture_fn = f"{camel_case_to_snake_case(model_cls.__name__)}.txt"
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema_description" / fixture_fn
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected
