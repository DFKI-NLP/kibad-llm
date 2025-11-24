import json
import os

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import DictConfig
import pytest

from kibad_llm.config import PROJ_ROOT
from tests.conftest import WRITE_FIXTURE_DATA, cfg_global

# strip extension to have nicer logging output, e.g. tests/test_extractors.py::test_extractor[simple]
# and exclude folders (without extension) and helper configs starting with "_"
AVAILABLE_EXTRACTORS = [
    os.path.splitext(extractor_yaml)[0]
    for extractor_yaml in os.listdir(PROJ_ROOT / "configs" / "extractor")
    if os.path.splitext(extractor_yaml)[1] != "" and not extractor_yaml.startswith("_")
]


@pytest.fixture(scope="function", params=AVAILABLE_EXTRACTORS)
def extractor_name(request) -> str:
    return request.param


@pytest.fixture(scope="function")
def cfg_predict_extractor(tmp_path, extractor_name) -> DictConfig:  # type: ignore
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[f"extractor={extractor_name}", "store_text_in_predictions=false"],
        config_name="predict.yaml",
    )

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_extractor(tmp_path, cfg_predict_extractor, extractor_name):

    HydraConfig().set_config(cfg_predict_extractor)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    text = markdown_data["text"]

    extractor = instantiate(cfg_predict_extractor.extractor, _convert_="all")
    result = extractor(text_id=file_name, text=text)

    expected_result_path = (
        PROJ_ROOT / "tests" / "fixtures" / "extractor" / f"{extractor_name}.{file_name}.json"
    )
    if WRITE_FIXTURE_DATA:
        # create directory if it does not exist
        os.makedirs(os.path.dirname(expected_result_path), exist_ok=True)
        # write fixture data
        with open(expected_result_path, "w") as f:
            json.dump(result, f, indent=2)

    with open(expected_result_path) as f:
        expected_result = json.load(f)

    # check top-level keys
    assert set(result) == set(expected_result)

    # just check keys since the actual values are not deterministic
    assert set(result["structured"]) == set(expected_result["structured"])
