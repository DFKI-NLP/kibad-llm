import json

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict
from tests.conftest import cfg_predict_global

PDF_DIR = PROJ_ROOT / "tests" / "fixtures" / "pdfs"
FILE_NAMES = sorted([f.name for f in PDF_DIR.glob("*.pdf")])
PREDICTION_DIR = PROJ_ROOT / "tests" / "fixtures" / "results"


@pytest.fixture(scope="module")
def cfg_predict_module(tmp_path_factory) -> DictConfig:  # type: ignore
    module_tmp_path = tmp_path_factory.mktemp("module")
    cfg = cfg_predict_global(out_dir=module_tmp_path)

    yield cfg

    GlobalHydra.instance().clear()


@pytest.fixture(scope="module")
def predictions_dict(cfg_predict_module) -> dict[str, dict]:

    with open_dict(cfg_predict_module):
        cfg_predict_module.pdf_directory = str(PDF_DIR)
        cfg_predict_module.disable_extraction_caching = True

    HydraConfig().set_config(cfg_predict_module)
    predict(cfg_predict_module)
    # read json line file from cfg_predict_module.output_file
    results = {}
    with open(cfg_predict_module.output_file) as f:
        lines = f.readlines()
        for line in lines:
            result = json.loads(line)
            results[result["file_name"]] = result

    return results


# small fixture to run test for each file and have good names in pytest output
@pytest.fixture(params=FILE_NAMES)
def file_name(request) -> str:
    return request.param


@pytest.mark.slow
def test_prediction(file_name, predictions_dict):
    prediction = predictions_dict[file_name]

    prediction_path = PREDICTION_DIR / f"{file_name}.json"

    # write fixture data
    # with open(prediction_path, "w") as f:
    #     json.dump(prediction, f, indent=4)

    # read fixture data
    with open(prediction_path) as f:
        result_expected = json.load(f)

    assert prediction["structured"] == result_expected["structured"]


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")
        cfg_predict.fast_dev_run = True
        cfg_predict.disable_extraction_caching = True

    HydraConfig().set_config(cfg_predict)
    predict(cfg_predict)

    # read json line file from cfg_predict.output_file
    results = []
    with open(cfg_predict.output_file) as f:
        lines = f.readlines()
        for line in lines:
            results.append(json.loads(line))

    assert len(results) == 1
    result = results[0]

    fixture_path = PROJ_ROOT / "tests" / "fixtures" / "results" / f"{result['file_name']}.json"

    # write fixture data
    # with open(fixture_path, "w") as f:
    #   json.dump(result, f, indent=4)

    # read fixture data
    with open(fixture_path) as f:
        fixture_data = json.load(f)
    assert result["structured"] == fixture_data["structured"]
