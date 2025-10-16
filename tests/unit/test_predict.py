import json

from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import extract_from_text, read_pdf_as_markdown


def test_read_pdf_as_markdown():
    file_name = "25ABQZIH.pdf"

    # get expected markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    markdown_expected = markdown_data["text"]

    result = read_pdf_as_markdown(
        file_name=file_name, base_path=PROJ_ROOT / "tests" / "fixtures" / "pdfs"
    )

    assert isinstance(result, dict)
    assert set(result) == {"text"}
    markdown = result["text"]

    assert markdown == markdown_expected


@pytest.mark.slow
def test_extract_from_text(tmp_path, cfg_predict):

    HydraConfig().set_config(cfg_predict)

    model = instantiate(cfg_predict.model)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    text = markdown_data["text"]

    template = instantiate(cfg_predict.template, _convert_="all")
    result = extract_from_text(text_id=file_name, text=text, model=model, **template)

    # just check keys since the actual values are not deterministic
    keys_expected = {"Bundesland", "Lebensraum", "Naturgroßraum", "Ökosystemtyp"}
    assert set(result["structured"]) == keys_expected
