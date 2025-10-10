from hydra.core.hydra_config import HydraConfig
from omegaconf import open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict_single


@pytest.mark.slow
def test_predict(tmp_path, cfg_predict_single):

    with open_dict(cfg_predict_single):
        cfg_predict_single.pdf_file = PROJ_ROOT / "tests" / "fixtures" / "pdfs" / "7T8NZA5Q.pdf"

    HydraConfig().set_config(cfg_predict_single)
    predict_single(cfg_predict_single)
