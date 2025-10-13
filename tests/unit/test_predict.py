import json

from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import extract_from_markdown


@pytest.mark.slow
def test_extract_from_markdown(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")
        cfg_predict.fast_dev_run = True

    HydraConfig().set_config(cfg_predict)

    model = instantiate(cfg_predict.model)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    markdown = markdown_data["markdown"]

    result = extract_from_markdown(
        markdown=markdown, template=cfg_predict.template.text, model=model
    )

    result_path = PROJ_ROOT / "tests" / "fixtures" / "results" / f"{file_name}.json"

    # read fixture data
    with open(result_path) as f:
        result_expected = json.load(f)

    # remove entries not in result
    del result_expected["file_name"]
    del result_expected["markdown"]

    assert result == result_expected
