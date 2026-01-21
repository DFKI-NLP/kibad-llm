import json

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict
from tests.conftest import WRITE_FIXTURE_DATA, cfg_global

PDF_DIR = PROJ_ROOT / "tests" / "fixtures" / "pdfs"
FILE_NAMES = sorted([f.name for f in PDF_DIR.glob("*.pdf")])
PREDICTION_DIR = PROJ_ROOT / "tests" / "fixtures" / "results"


@pytest.fixture(scope="module")
def cfg_predict_module(tmp_path_factory) -> DictConfig:  # type: ignore
    module_tmp_path = tmp_path_factory.mktemp("module")
    cfg = cfg_global(config_name="predict.yaml", out_dir=module_tmp_path)

    yield cfg

    GlobalHydra.instance().clear()


@pytest.fixture(scope="module")
def predictions_dict(cfg_predict_module) -> dict[str, dict]:

    with open_dict(cfg_predict_module):
        cfg_predict_module.pdf_directory = str(PDF_DIR)

    HydraConfig().set_config(cfg_predict_module)
    job_return_value = predict(cfg_predict_module)

    with open(job_return_value["output_file"]) as f:
        lines = f.readlines()

    # create result as dict keyed by file_name
    results = {}
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

    if WRITE_FIXTURE_DATA:
        prediction_path.parent.mkdir(parents=True, exist_ok=True)
        # write fixture data
        with open(prediction_path, "w") as f:
            json.dump(prediction, f, indent=4, ensure_ascii=False)

    # read fixture data
    with open(prediction_path) as f:
        result_expected = json.load(f)

    # just check keys since the actual values are not deterministic
    assert set(prediction["structured"]) == set(result_expected["structured"])


@pytest.mark.slow
def test_predict_fast_dev_run(tmp_path, cfg_predict):

    with open_dict(cfg_predict):
        cfg_predict.pdf_directory = str(PDF_DIR)
        cfg_predict.fast_dev_run = True

    HydraConfig().set_config(cfg_predict)
    job_return_value = predict(cfg_predict)

    with open(job_return_value["output_file"]) as f:
        lines = f.readlines()
    results = [json.loads(line) for line in lines]

    assert len(results) == 1
    result = results[0]

    fixture_path = PREDICTION_DIR / f"{result['file_name']}.json"

    # write fixture data
    # with open(fixture_path, "w") as f:
    #   json.dump(result, f, indent=4, ensure_ascii=False)

    # read fixture data
    with open(fixture_path) as f:
        fixture_data = json.load(f)

    # just check keys since the actual values are not deterministic
    assert set(result["structured"]) == set(fixture_data["structured"])


@pytest.fixture(params=["too_long", "missing_response_content"])
def error_type(request) -> str:
    return request.param


@pytest.fixture(scope="function")
def cfg_predict_pdf_errors(tmp_path, error_type) -> DictConfig:  # type: ignore
    overrides = [
        # don't compress to be able to read error messages easily
        "output_file_name=predictions.jsonl",
    ]
    if error_type in ["too_long"]:
        # we need the text to check for the length, so enable store_text_in_predictions
        overrides.append("store_text_in_predictions=true")
    if error_type in ["missing_response_content"]:
        # use a more complex schema that is more likely to fail
        overrides.append("experiment/predict=faktencheck_core_fields_schema_with_evidence")

    cfg = cfg_global(
        config_name="predict.yaml",
        out_dir=tmp_path,
        overrides=overrides,
    )

    with open_dict(cfg):
        cfg.pdf_directory = str(PROJ_ROOT / "tests" / "fixtures" / "pdfs_error" / error_type)

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_prediction_on_pdf_errors(cfg_predict_pdf_errors, error_type):
    job_return_value = predict(cfg_predict_pdf_errors)

    with open(job_return_value["output_file"]) as f:
        lines = f.readlines()

    # create result as dict keyed by file_name
    results = {}
    for line in lines:
        result = json.loads(line)
        results[result["file_name"]] = result

    # check long PDF error
    if error_type == "too_long":
        file_name = "2E9XWUUE.pdf"
        assert file_name in results
        result = results[file_name]
        # assert that there was some quite long input text
        text = result.get("text", None)
        assert text is not None and len(text) > 1_000_000
        # assert that there is no structured output ...
        assert result.get("structured", None) is None
        # ... but an error message about max tokens
        error = result.get("error", None)
        assert error is not None
        assert error.startswith("ValueError:")
        assert "Error code: 400" in error
        assert "'type': 'BadRequestError'" in error
        # check that we got a negative max_tokens error message
        assert "'message': 'max_tokens must be at least 1, got -" in error
    elif error_type == "missing_response_content":
        file_name = "3Z5BFIBL.pdf"
        assert file_name in results
        result = results[file_name]
        # assert that there is no structured output ...
        assert result.get("structured", None) is None
        # ... but an error message about missing response content
        error = result.get("error", None)
        assert error is not None
        assert error.startswith("MissingResponseContentError:")
    else:
        pytest.fail(f"Unhandled error_type fixture: {error_type}")
