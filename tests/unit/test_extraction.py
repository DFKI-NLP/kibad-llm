import json

from hydra.core.hydra_config import HydraConfig
from hydra.utils import instantiate
from llama_index.core import Settings
import pytest

from kibad_llm.config import PROJ_ROOT


@pytest.mark.slow
def test_extractor(tmp_path, cfg_predict):

    HydraConfig().set_config(cfg_predict)

    file_name = "25ABQZIH.pdf"

    # read markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    text = markdown_data["text"]

    extractor = instantiate(cfg_predict.extractor, _convert_="all")
    result = extractor(text_id=file_name, text=text)

    # just check keys since the actual values are not deterministic
    keys_expected = {"Bundesland", "Lebensraum", "Naturgroßraum", "Ökosystemtyp"}
    assert set(result["structured"]) == keys_expected
