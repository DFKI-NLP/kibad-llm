import json

from pydantic import BaseModel
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.types import (
    EcosystemStudyFeaturesSimple,
    EcosystemStudyFeaturesWithoutCompounds,
)
from tests.conftest import WRITE_FIXTURE_DATA

MODEL2FIXTURE = {
    EcosystemStudyFeaturesWithoutCompounds: "ecosystem_study_features_without_compounds.txt",
    EcosystemStudyFeaturesSimple: "ecosystem_study_features_simple.txt",
}


@pytest.mark.parametrize("model_cls", list(MODEL2FIXTURE))
def test_type(model_cls: type[BaseModel]):
    schema = model_cls.model_json_schema()
    path_expected = PROJ_ROOT / "tests" / "fixtures" / "schema" / MODEL2FIXTURE[model_cls]
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema == expected
