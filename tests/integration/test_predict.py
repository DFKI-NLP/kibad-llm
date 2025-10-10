from hydra.core.hydra_config import HydraConfig
from omegaconf import open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict


@pytest.mark.slow
def test_predict(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")
        cfg_predict.fast_dev_run = True

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)
