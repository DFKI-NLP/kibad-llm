from hydra.core.hydra_config import HydraConfig
from omegaconf import open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict_single, predict


@pytest.mark.slow
def test_predict_single(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_file = PROJ_ROOT / "tests" / "fixtures" / "pdfs" / "7T8NZA5Q.pdf"

    HydraConfig().set_config(cfg_predict)
    predict_single(cfg_predict)


@pytest.mark.slow
def test_predict(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = PROJ_ROOT / "tests" / "fixtures" / "pdfs"

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = PROJ_ROOT / "tests" / "fixtures" / "pdfs"
        cfg_predict.fast_dev_run = True

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)