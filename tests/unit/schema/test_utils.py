from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.types import EcosystemStudyFeatures
from kibad_llm.schema.utils import build_schema_description
from tests.conftest import WRITE_FIXTURE_DATA


def test_build_schema_description():
    description = build_schema_description(EcosystemStudyFeatures.model_json_schema())
    path_expected = (
        PROJ_ROOT / "tests" / "fixtures" / "schema" / "description_ecosystem_study_features.txt"
    )
    if WRITE_FIXTURE_DATA:
        with open(path_expected, "w") as f:
            f.write(description)

    with open(path_expected) as f:
        expected = f.read()
    assert description == expected
