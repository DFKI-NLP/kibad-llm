from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.types import (
    EcosystemStudyFeaturesSimple,
    EcosystemStudyFeaturesWithoutCompounds,
)
from kibad_llm.schema.utils import build_schema_description
from tests.conftest import WRITE_FIXTURE_DATA

MODEL2FIXTURE = {
    EcosystemStudyFeaturesWithoutCompounds: "ecosystem_study_features_without_compounds.txt",
    EcosystemStudyFeaturesSimple: "ecosystem_study_features_simple.txt",
}


@pytest.mark.parametrize("model_cls", list(MODEL2FIXTURE))
def test_build_schema_description(model_cls: type[BaseModel]):
    description = build_schema_description(model_cls.model_json_schema(by_alias=False))
    path_expected = (
        PROJ_ROOT / "tests" / "fixtures" / "schema_description" / MODEL2FIXTURE[model_cls]
    )
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected
