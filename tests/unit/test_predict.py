import json

from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from omegaconf import open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import extract_from_markdown, read_pdf_as_markdown


def test_read_pdf_as_markdown():
    file_name = "25ABQZIH.pdf"

    # get expected markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    markdown_expected = markdown_data["markdown"]

    result = read_pdf_as_markdown(
        file_name=file_name, base_path=PROJ_ROOT / "tests" / "fixtures" / "pdfs"
    )

    assert isinstance(result, dict)
    assert set(result) == {"markdown"}
    markdown = result["markdown"]

    assert markdown == markdown_expected


@pytest.mark.slow
def test_extract_from_markdown(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")
        cfg_predict.fast_dev_run = True
        cfg_predict.disable_extraction_caching = True

    HydraConfig().set_config(cfg_predict)

    model = instantiate(cfg_predict.model)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    markdown = markdown_data["markdown"]

    template = instantiate(cfg_predict.template, _convert_="all")
    result = extract_from_markdown(file_name=file_name, markdown=markdown, model=model, **template)

    # just check keys since the actual values are not deterministic
    keys_expected = {"Bundesland", "Lebensraum", "Naturgroßraum", "Ökosystemtyp"}
    assert set(result["structured"]) == keys_expected
