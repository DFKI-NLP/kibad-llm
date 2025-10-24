import json
import os

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import DictConfig
import pytest

from kibad_llm.config import PROJ_ROOT
from tests.conftest import cfg_global

# strip extension to have nicer logging output, e.g. tests/test_extractors.py::test_extractor[simple]
# and exclude helper configs starting with "_"
AVAILABLE_EXTRACTORS = [
    os.path.splitext(extractor_yaml)[0]
    for extractor_yaml in os.listdir(PROJ_ROOT / "configs" / "extractor")
    if not extractor_yaml.startswith("_")
]


@pytest.fixture(scope="function", params=AVAILABLE_EXTRACTORS)
def cfg_predict_extractor(tmp_path, request) -> DictConfig:  # type: ignore
    cfg = cfg_global(
        out_dir=tmp_path, overrides=[f"extractor={request.param}"], config_name="predict.yaml"
    )

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_extractor(tmp_path, cfg_predict_extractor):

    HydraConfig().set_config(cfg_predict_extractor)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    text = markdown_data["text"]

    extractor = instantiate(cfg_predict_extractor.extractor, _convert_="all")
    result = extractor(text_id=file_name, text=text)

    # just check keys since the actual values are not deterministic
    keys_expected = {"Bundesland", "Lebensräume", "Naturgroßräume", "Ökosystemtyp"}
    assert set(result["structured"]) == keys_expected
