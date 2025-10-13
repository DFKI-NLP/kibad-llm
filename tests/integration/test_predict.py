import json

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

    # read json line file from cfg_predict.output_file
    results = []
    with open(cfg_predict.output_file) as f:
        lines = f.readlines()
        for line in lines:
            results.append(json.loads(line))

    for result in results:
        fixture_path = PROJ_ROOT / "tests" / "fixtures" / "results" / f"{result['file_name']}.json"

        # write fixture data
        # with open(fixture_path, "w") as f:
        #    json.dump(result, f, indent=4)

        # read fixture data
        with open(fixture_path) as f:
            result_expected = json.load(f)

        assert result["structured"] == result_expected["structured"]


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs")
        cfg_predict.fast_dev_run = True

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
