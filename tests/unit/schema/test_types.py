import json
import re
from typing import Any

import jsonschema
from pydantic import BaseModel
import pytest
import yaml

from kibad_llm.config import PROJ_ROOT
from kibad_llm.llms.openai import make_openai_strict_json_schema
from kibad_llm.schema.types import (
    BiodiversityFacetEnum,
    CategoricalBiodiversityFacetEnum,
    CategoricalEinflussEnum,
    DirectionalEinflussEnum,
    EcosystemStudyEcosystemServiceTrends,
    EcosystemStudyEcosystemServiceTrendsWithoutHabitat,
    EinflussEnum,
    GradientBiodiversityFacetEnum,
    HabitatEnum,
    OtherBiodiversityFacetEnum,
    ThemenkomplexEnum,
    ÖSLEnum,
)
from kibad_llm.schema.utils import (
    METADATA_SCHEMA_WITH_EVIDENCE,
    wrap_terminals_with_metadata,
)
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
        path_expected.parent.mkdir(parents=True, exist_ok=True)
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
        path_expected.parent.mkdir(parents=True, exist_ok=True)
        with open(path_expected, "w") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

    with open(path_expected) as f:
        expected = json.load(f)
    assert schema == expected


CATEGORICAL_FACETS = {facet.value for facet in CategoricalBiodiversityFacetEnum}
GRADIENT_FACETS = {facet.value for facet in GradientBiodiversityFacetEnum}
OTHER_FACETS = {facet.value for facet in OtherBiodiversityFacetEnum}


def _prompt_oesl_by_themenkomplex() -> dict[str, list[str]]:
    """Read the closed ÖSL list per Themenkomplex from the ecosystem-service prompt."""
    path = PROJ_ROOT / "configs" / "extractor" / "prompt_template" / "ecosystem_service.yaml"
    prompt = yaml.safe_load(path.read_text(encoding="utf-8"))["system_message"]
    section = prompt.split("## Themenkomplexe")[1].split("## ÖSL/ÖSF")[0]
    names = "|".join(re.escape(theme.value) for theme in ThemenkomplexEnum)
    matches = re.findall(
        rf"^({names})[^\n]*:\n.*?Zugehörige ÖSL/ÖSF:(.*?)\.\n", section, flags=re.S | re.M
    )
    return {
        name: [" ".join(value.split()) for value in values.split(";")] for name, values in matches
    }


def test_prompt_lists_each_oesl_value_under_exactly_one_themenkomplex() -> None:
    """Keep the closed ÖSL list of the prompt in sync with ÖSLEnum."""
    by_theme = _prompt_oesl_by_themenkomplex()
    assert set(by_theme) == {theme.value for theme in ThemenkomplexEnum}
    prompt_values = [value for values in by_theme.values() for value in values]
    assert len(prompt_values) == len(set(prompt_values))
    assert set(prompt_values) == {value.value for value in ÖSLEnum}


def test_facet_groups_partition_all_facets() -> None:
    """Every facet belongs to exactly one group, so that it is reachable in exactly one variant."""
    groups = [CATEGORICAL_FACETS, GRADIENT_FACETS, OTHER_FACETS]
    assert sum(len(group) for group in groups) == len(BiodiversityFacetEnum)
    assert set().union(*groups) == {facet.value for facet in BiodiversityFacetEnum}


def _allowed_einfluss(facet: str) -> set[str]:
    """Return the Einfluss values that the variants allow for a facet."""
    if facet in CATEGORICAL_FACETS:
        return {value.value for value in CategoricalEinflussEnum}
    if facet in GRADIENT_FACETS:
        return {value.value for value in DirectionalEinflussEnum}
    return {value.value for value in EinflussEnum}


@pytest.mark.parametrize(
    ("model_cls", "extra_fields"),
    [
        (EcosystemStudyEcosystemServiceTrendsWithoutHabitat, {}),
        (EcosystemStudyEcosystemServiceTrends, {"Lebensraum_Gruppiert": HabitatEnum.WALD.value}),
    ],
)
@pytest.mark.parametrize("schema_form", ["plain", "evidence", "openai_strict"])
def test_variants_restrict_einfluss_by_facet(model_cls, extra_fields, schema_form) -> None:
    """The Einfluss restriction holds in each schema form sent to a guided-decoding backend."""
    schema = model_cls.model_json_schema(by_alias=False)
    wrapped = schema_form != "plain"
    if wrapped:
        schema = wrap_terminals_with_metadata(schema, METADATA_SCHEMA_WITH_EVIDENCE)
    if schema_form == "openai_strict":
        schema = make_openai_strict_json_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    def value(content: str) -> str | dict[str, str]:
        """Wrap a terminal value if the schema expects evidence metadata."""
        return {"content": content, "evidence_anchor": "x"} if wrapped else content

    for facet in BiodiversityFacetEnum:
        for einfluss in EinflussEnum:
            fields = {
                "ÖSL": ÖSLEnum.ZERSETZUNG.value,
                "Themenkomplex": ThemenkomplexEnum.KOHLENSTOFFKREISLAUF.value,
                "Biodiv_Facette": facet.value,
                "Einfluss": einfluss.value,
                **extra_fields,
            }
            entry: dict[str, Any] = {name: value(content) for name, content in fields.items()}
            entry["Arten"] = []
            is_valid = validator.is_valid({"ecosystem_service_trends": [entry]})
            assert is_valid == (einfluss.value in _allowed_einfluss(facet.value))
