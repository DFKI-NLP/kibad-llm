"""Tests that the ecosystem-service prompt and experiments compose for different habitats."""

from hydra.core.global_hydra import GlobalHydra
from hydra.utils import instantiate
import pytest

from tests.conftest import cfg_global


@pytest.fixture(autouse=True)
def clear_hydra():
    """Reset global Hydra state after each composition."""
    yield
    GlobalHydra.instance().clear()


def _compose(tmp_path, *overrides: str):
    """Compose a prediction config and return its prompt and extraction schema."""
    cfg = cfg_global(overrides=list(overrides), out_dir=tmp_path)
    schema = instantiate(cfg.extractor.schema, _convert_="all")
    return cfg.extractor.prompt_template.system_message, schema


def _entry_properties(schema: dict) -> set[str]:
    """Collect the field names of all ecosystem-service variants."""
    return {
        name
        for variant in schema["properties"]["ecosystem_service_trends"]["items"]["anyOf"]
        for name in schema["$defs"][variant["$ref"].rsplit("/", 1)[-1]]["properties"]
    }


def test_forest_is_the_default_habitat(tmp_path) -> None:
    """The forest experiment keeps its habitat wording and has no habitat field."""
    prompt, schema = _compose(tmp_path, "experiment/predict=ecosystemservice_trends")
    assert "Ökosystemleistungen im Lebensraum 'Wald', meist" in prompt
    assert "für jeden Lebensraum" not in prompt
    assert "${" not in prompt
    assert "Lebensraum_Gruppiert" not in _entry_properties(schema)


def test_single_other_habitat_can_be_set(tmp_path) -> None:
    """A single other habitat only needs the prompt wording."""
    prompt, schema = _compose(
        tmp_path,
        "experiment/predict=ecosystemservice_trends",
        '+ecosystem_service_prompt.habitat_scope="im Lebensraum Urbane Räume"',
    )
    assert "Ökosystemleistungen im Lebensraum Urbane Räume, meist" in prompt
    assert "'Wald'" not in prompt.split("## Was zählt")[0]
    assert "Lebensraum_Gruppiert" not in _entry_properties(schema)


def test_all_habitats_experiment(tmp_path) -> None:
    """The all-habitats experiment adds the habitat field and its instruction."""
    prompt, schema = _compose(tmp_path, "experiment/predict=ecosystemservice_trends_all_habitats")
    assert "Ökosystemleistungen in einem bzw. mehreren Lebensräumen, meist" in prompt
    assert "nicht mehr. Betrifft eine Beziehung mehrere Lebensräume" in prompt
    assert "'Wald'" not in prompt.split("## Was zählt")[0]
    assert "Lebensraum_Gruppiert" in _entry_properties(schema)
